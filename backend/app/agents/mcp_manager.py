"""
MCP (Model Context Protocol) integration module.

Manages connections to multiple MCP Servers and provides
a unified tool interface for the Agent Swarm.
"""

import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.tools import load_mcp_tools
from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPManager:
    """
    Manages MCP Server connections and tool discovery.

    Responsibilities:
    - Load MCP server configurations
    - Establish and maintain connections
    - Discover available tools from each server
    - Convert MCP tools to LangChain-compatible tools
    - Health monitoring of MCP servers
    """

    def __init__(self) -> None:
        self._servers: dict[str, dict] = {}  # name -> config
        self._sessions: dict[str, ClientSession] = {}
        self._tools: list[Any] = []
        self._exit_stack = AsyncExitStack()
        logger.info("🔧 MCPManager initialized")

    async def load_config(self, config_path: str) -> None:
        """Load MCP server configurations from JSON file."""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"MCP config not found at {config_path}")
            return

        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                data = json.load(f)
                self._servers = data.get("mcpServers", data)
                logger.info(f"Loaded {len(self._servers)} MCP servers from config")
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")

    async def connect_all(self) -> None:
        """Establish connections to all configured MCP servers."""
        if not self._servers:
            logger.info("No MCP servers configured.")
            return

        for name, config in self._servers.items():
            if name in self._sessions:
                continue

            try:
                server_type = config.get("type", "stdio")
                if server_type == "stdio":
                    command = config.get("command")
                    args = config.get("args", [])
                    env = config.get("env", None)

                    server_params = StdioServerParameters(command=command, args=args, env=env)
                    # Enter stdio transport
                    stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
                    read, write = stdio_transport[0], stdio_transport[1]

                    # Enter client session
                    session = await self._exit_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    self._sessions[name] = session

                    # Discover tools
                    agent_tools_iterable = await load_mcp_tools(session)
                    agent_tools = list(agent_tools_iterable) if agent_tools_iterable else []
                    self._tools.extend(agent_tools)

                    logger.info(f"Connected to MCP Server: {name} with {len(agent_tools)} tools.")
                else:
                    logger.warning(f"Unsupported MCP transport: {server_type} for server {name}")
            except Exception as e:
                logger.error(f"Failed to connect MCP server '{name}': {e}")

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        await self._exit_stack.aclose()
        self._sessions.clear()
        self._tools.clear()
        logger.info("Disconnected from all MCP servers")

    def get_tools(self, server_name: str | None = None) -> list[Any]:
        """
        Get available tools, optionally filtered by server.

        Returns LangChain-compatible Tool objects.
        """
        return self._tools

    async def discover_tools(self, query: str, limit: int = 15) -> list[Any]:
        """
        [P2 Upgrade] Discover MCP tools relevant using Semantic Search.
        """
        if not self._tools:
            return []

        try:
            from app.core.embeddings import get_embedding_service
            import numpy as np
            
            embedder = get_embedding_service()
            query_vector = await embedder.aembed_query(query)
            
            tool_texts = [
                f"MCP Tool: {getattr(t, 'name', '')}. Desc: {getattr(t, 'description', '')}"
                for t in self._tools
            ]
            
            # Since we don't cache MCP embeddings yet (dynamic), we do it on the fly
            # In production, we'd cache these per-session.
            tool_vectors = await embedder.aembed_documents(tool_texts)
            
            q_vec = np.array(query_vector)
            t_vecs = np.array(tool_vectors)
            
            similarities = np.dot(t_vecs, q_vec) / (
                np.linalg.norm(t_vecs, axis=1) * np.linalg.norm(q_vec)
            )
            
            idx = np.argsort(similarities)[::-1]
            results = [self._tools[i] for i in idx[:limit] if similarities[i] > 0.3]
            
            if results:
                logger.debug(f"🧬 [MCP Semantic] Found {len(results)} relevant tools for query '{query}'")
                return results

        except Exception as e:
            logger.debug(f"[MCP Semantic] Search fallback to keyword: {e}")

        # Fallback keyword logic
        query_words = set(query.lower().split())
        scored_tools = []
        for tool in self._tools:
            desc = getattr(tool, "description", "").lower()
            name = getattr(tool, "name", "").lower()
            score = sum(2 if word in name else 0 for word in query_words)
            score += sum(1 if word in desc else 0 for word in query_words)
            if score > 0: scored_tools.append((score, tool))

        scored_tools.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored_tools[:limit]] or self._tools[:limit]

    async def health_check(self) -> dict[str, bool]:
        """Check connectivity to all MCP servers."""
        status = {}
        for name in self._servers:
            status[name] = name in self._sessions
        return status
