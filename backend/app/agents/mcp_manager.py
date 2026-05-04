"""
MCP (Model Context Protocol) integration module.

Manages connections to multiple MCP Servers and provides
a unified tool interface for the Agent Swarm.
"""

import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from loguru import logger
from langchain_mcp_adapters.tools import load_mcp_tools
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
            with open(path, "r", encoding="utf-8") as f:
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

    async def reconnect_all(self, config_path: str | None = None) -> None:
        """
        Disconnect everything and reconnect from a (possibly updated) config file.
        Used by the management API after CRUD changes.
        """
        try:
            await self.disconnect_all()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Disconnect during reconnect raised: {e}")
        # Reset exit stack since aclose() invalidated the previous one
        self._exit_stack = AsyncExitStack()
        if config_path:
            await self.load_config(config_path)
        await self.connect_all()
        logger.info("🔁 MCP servers reconnected after config change")

    def get_servers_config(self) -> dict[str, dict]:
        """Return the in-memory copy of all server configs."""
        return dict(self._servers)

    def update_server_config(self, name: str, config: dict) -> None:
        """Add or replace a single server's config (in-memory only)."""
        self._servers[name] = config

    def remove_server_config(self, name: str) -> bool:
        """Remove a single server config (in-memory only). Returns True if existed."""
        return self._servers.pop(name, None) is not None

    @staticmethod
    def persist_config(config_path: str, servers: dict[str, dict]) -> None:
        """Write the merged servers map back to the JSON file."""
        path = Path(config_path)
        payload = {"mcpServers": servers}
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"💾 Persisted {len(servers)} MCP server(s) to {config_path}")

    def get_tools(self, server_name: str | None = None) -> list[Any]:
        """
        Get available tools, optionally filtered by server.

        Returns LangChain-compatible Tool objects.
        """
        return self._tools

    async def health_check(self) -> dict[str, bool]:
        """Check connectivity to all MCP servers."""
        status = {}
        for name in self._servers.keys():
            status[name] = name in self._sessions
        return status
