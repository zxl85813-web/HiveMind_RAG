"""
Tools for MCP Builder Skill.
"""

from typing import Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import json

class McpServerConfig(BaseModel):
    name: str = Field(description="Name of the MCP server")
    command: str = Field(description="Command to run the server (e.g., 'npx')")
    args: list[str] = Field(description="Arguments for the command")
    type: str = Field(description="Type of connection (stdio or sse)")

@tool(args_schema=McpServerConfig)
async def generate_mcp_config(name: str, command: str, args: list[str], type: str) -> str:
    """Generate a valid MCP server configuration snippet."""
    config = {
        name: {
            "command": command,
            "args": args,
            "type": type
        }
    }
    return json.dumps(config, indent=2)

TOOLS = [
    generate_mcp_config
]
