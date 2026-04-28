"""
MCP (Model Context Protocol) Integration — M9.4.1
===================================================
管理 MCP Server 连接和工具发现。

配置文件格式 (mcp_servers.json):
{
  "servers": {
    "database": {
      "type": "sse",
      "url": "http://localhost:8001/sse"
    },
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  }
}

用法:
    manager = MCPManager()
    await manager.load_config("mcp_servers.json")
    await manager.connect_all()
    tools = manager.get_tools()  # LangChain-compatible Tool 列表
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


class MCPServerConfig:
    """单个 MCP Server 的配置。"""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.server_type: str = config.get("type", "stdio")  # stdio | sse | http
        self.url: str | None = config.get("url")
        self.command: str | None = config.get("command")
        self.args: list[str] = config.get("args", [])
        self.env: dict[str, str] = config.get("env", {})
        self.is_connected: bool = False
        self.tools: list[Any] = []
        self.error: str | None = None


class MCPManager:
    """
    管理 MCP Server 连接和工具发现。

    职责:
    - 从 JSON 配置文件加载 MCP Server 定义
    - 建立和维护连接
    - 发现各 Server 提供的工具
    - 将 MCP 工具转换为 LangChain 兼容格式
    - 健康监控
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: list[Any] = []
        self._client: Any | None = None  # MultiServerMCPClient instance
        logger.info("🔧 MCPManager initialized")

    async def load_config(self, config_path: str | None = None) -> int:
        """
        从 JSON 文件加载 MCP Server 配置。

        Args:
            config_path: 配置文件路径，默认使用 settings.MCP_SERVERS_CONFIG_PATH

        Returns:
            加载的 Server 数量
        """
        path = Path(config_path or settings.MCP_SERVERS_CONFIG_PATH)

        # 尝试多个可能的路径
        candidates = [
            path,
            settings.BASE_DIR / path,
            settings.BASE_DIR / "app" / path,
        ]

        config_data: dict[str, Any] | None = None
        for candidate in candidates:
            if candidate.exists():
                try:
                    config_data = json.loads(candidate.read_text(encoding="utf-8"))
                    logger.info(f"[MCPManager] Loaded config from: {candidate}")
                    break
                except Exception as e:
                    logger.warning(f"[MCPManager] Failed to parse {candidate}: {e}")

        if not config_data:
            logger.info("[MCPManager] No MCP config file found. MCP tools disabled.")
            return 0

        servers = config_data.get("servers", config_data.get("mcpServers", {}))
        for name, server_config in servers.items():
            if server_config.get("disabled", False):
                logger.debug(f"[MCPManager] Server '{name}' is disabled, skipping.")
                continue
            self._servers[name] = MCPServerConfig(name, server_config)

        logger.info(f"[MCPManager] Loaded {len(self._servers)} MCP server configs: {list(self._servers.keys())}")
        return len(self._servers)

    async def connect_all(self) -> dict[str, bool]:
        """
        建立到所有已配置 MCP Server 的连接。

        Returns:
            {server_name: connected} 映射
        """
        if not self._servers:
            return {}

        results: dict[str, bool] = {}

        for name, server in self._servers.items():
            try:
                tools = await self._connect_server(server)
                server.is_connected = True
                server.tools = tools
                self._tools.extend(tools)
                results[name] = True
                logger.info(f"[MCPManager] ✅ Connected to '{name}': {len(tools)} tools discovered")
            except Exception as e:
                server.is_connected = False
                server.error = str(e)
                results[name] = False
                logger.warning(f"[MCPManager] ❌ Failed to connect to '{name}': {e}")

        logger.info(
            f"[MCPManager] Connection summary: {sum(results.values())}/{len(results)} servers, "
            f"{len(self._tools)} total tools"
        )
        return results

    async def _connect_server(self, server: MCPServerConfig) -> list[Any]:
        """
        连接单个 MCP Server 并发现其工具。

        尝试使用 langchain-mcp-adapters，不可用时降级为 httpx 直连。
        """
        if server.server_type == "sse" and server.url:
            return await self._connect_sse(server)
        elif server.server_type == "stdio" and server.command:
            return await self._connect_stdio(server)
        else:
            raise ValueError(f"Unsupported server type: {server.server_type}")

    async def _connect_sse(self, server: MCPServerConfig) -> list[Any]:
        """通过 SSE 连接 MCP Server。"""
        try:
            # 尝试使用 langchain-mcp-adapters
            from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore

            client = MultiServerMCPClient({
                server.name: {"url": server.url, "transport": "sse"}
            })
            tools = await client.get_tools()
            return tools
        except ImportError:
            logger.debug("[MCPManager] langchain-mcp-adapters not installed, using httpx fallback")
            return await self._discover_tools_via_http(server)

    async def _connect_stdio(self, server: MCPServerConfig) -> list[Any]:
        """通过 stdio 连接 MCP Server。"""
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore

            client = MultiServerMCPClient({
                server.name: {
                    "command": server.command,
                    "args": server.args,
                    "env": server.env,
                    "transport": "stdio",
                }
            })
            tools = await client.get_tools()
            return tools
        except ImportError:
            logger.warning(
                f"[MCPManager] langchain-mcp-adapters required for stdio transport. "
                f"Install: pip install langchain-mcp-adapters"
            )
            return []

    async def _discover_tools_via_http(self, server: MCPServerConfig) -> list[Any]:
        """
        降级方案：通过 HTTP 直接调用 MCP Server 的 tools/list 端点。
        返回简单的 Tool 描述字典（非 LangChain Tool 对象）。
        """
        import httpx

        base_url = (server.url or "").rstrip("/").replace("/sse", "")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{base_url}/tools/list",
                    json={},
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tools = data.get("tools", [])
                    logger.info(f"[MCPManager] Discovered {len(tools)} tools via HTTP from {server.name}")
                    return [
                        {
                            "name": t.get("name", ""),
                            "description": t.get("description", ""),
                            "input_schema": t.get("inputSchema", {}),
                            "server": server.name,
                            "_mcp_raw": True,
                        }
                        for t in tools
                    ]
        except Exception as e:
            logger.debug(f"[MCPManager] HTTP tool discovery failed for {server.name}: {e}")

        return []

    async def disconnect_all(self) -> None:
        """断开所有 MCP Server 连接。"""
        for server in self._servers.values():
            server.is_connected = False
            server.tools = []
        self._tools.clear()
        self._client = None
        logger.info("[MCPManager] All servers disconnected.")

    def get_tools(self, server_name: str | None = None) -> list[Any]:
        """
        获取可用工具列表，可按 Server 过滤。

        Returns:
            LangChain-compatible Tool 对象列表（或降级的 dict 描述）
        """
        if server_name:
            server = self._servers.get(server_name)
            return server.tools if server else []
        return list(self._tools)

    async def health_check(self) -> dict[str, dict[str, Any]]:
        """检查所有 MCP Server 的连接状态。"""
        status: dict[str, dict[str, Any]] = {}
        for name, server in self._servers.items():
            status[name] = {
                "type": server.server_type,
                "connected": server.is_connected,
                "tool_count": len(server.tools),
                "error": server.error,
            }
        return status

    def get_tool_names(self) -> list[str]:
        """获取所有已发现工具的名称列表。"""
        names = []
        for tool in self._tools:
            if isinstance(tool, dict):
                names.append(tool.get("name", "unknown"))
            elif hasattr(tool, "name"):
                names.append(tool.name)
        return names


# ── 单例 ──────────────────────────────────────────────────────────────────────

_mcp_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
