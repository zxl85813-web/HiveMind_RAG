"""Standalone MCP stdio server exposing the quote-intelligence pipeline.

Wire it up in ``backend/mcp_servers.json`` to make these tools available
to any MCP-aware agent (including this project's SwarmOrchestrator):

    {
      "mcpServers": {
        "quote_intel": {
          "command": "python",
          "args": ["../mcp-servers/quote-intel-server/server.py"],
          "type": "stdio"
        }
      }
    }

Tools exposed:
    - quote_intel_run            : full pipeline (mask -> top-N -> LLM -> unmask)
    - quote_intel_fetch_masked   : fetch + mask + top-N only (no LLM)

The server delegates to :class:`app.services.quote.QuoteIntelligenceService`
so behaviour stays in lock-step with the in-process skill and REST routes.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Make the backend package importable when launched from the repo root.
_HERE = Path(__file__).resolve()
_BACKEND = _HERE.parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import mcp.types as types  # noqa: E402
from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402


app = Server("quote-intel")


_RUN_SCHEMA = {
    "type": "object",
    "properties": {
        "tenant_id": {"type": "string", "default": "default"},
        "top_n": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
        "ranking": {
            "type": "string",
            "enum": ["amount_weighted_recency", "amount_desc", "recency"],
            "default": "amount_weighted_recency",
        },
        "skip_llm": {"type": "boolean", "default": False},
    },
}


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="quote_intel_run",
            description=(
                "Run the full quote-intelligence pipeline for a tenant: "
                "fetch -> mask PII -> top-N rank -> LLM analysis -> unmask. "
                "Returns masked records, masked LLM report, and the final "
                "PII-restored report."
            ),
            inputSchema=_RUN_SCHEMA,
        ),
        types.Tool(
            name="quote_intel_fetch_masked",
            description=(
                "Fetch + mask + top-N only — does NOT call the LLM. Use to "
                "preview what would be sent to the LLM."
            ),
            inputSchema=_RUN_SCHEMA,
        ),
    ]


async def _do_run(arguments: dict, *, force_skip_llm: bool = False) -> dict:
    from app.core.database import async_session_factory
    from app.services.quote import QuoteIntelligenceService

    tenant_id = arguments.get("tenant_id") or os.environ.get("MCP_TENANT_ID", "default")
    top_n = int(arguments.get("top_n", 5))
    ranking = arguments.get("ranking", "amount_weighted_recency")
    skip_llm = bool(arguments.get("skip_llm", False)) or force_skip_llm

    svc = QuoteIntelligenceService()
    async with async_session_factory() as db:
        result = await svc.run(
            db,
            tenant_id=tenant_id,
            top_n=max(1, min(top_n, 50)),
            ranking=ranking,
            skip_llm=skip_llm,
        )
    return {
        "fetched_count": result.fetched_count,
        "selected_count": result.selected_count,
        "ranking": result.ranking,
        "masked_token_count": result.token_count,
        "masked_records": result.masked_records,
        "masked_report": result.masked_report,
        "final_report": result.final_report,
    }


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "quote_intel_run":
        out = await _do_run(arguments)
    elif name == "quote_intel_fetch_masked":
        out = await _do_run(arguments, force_skip_llm=True)
    else:
        raise ValueError(f"Unknown tool: {name}")
    return [types.TextContent(type="text", text=json.dumps(out, ensure_ascii=False))]


async def main() -> None:
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
