# quote-intel MCP server

Standalone stdio MCP server exposing the **end-to-end quote-intelligence
pipeline** as a pair of tools:

| Tool | Description |
|---|---|
| `quote_intel_run` | Full pipeline: fetch -> mask PII -> top-N -> LLM -> unmask |
| `quote_intel_fetch_masked` | Fetch + mask + top-N only (LLM stage skipped) |

The server delegates to `app.services.quote.QuoteIntelligenceService`
(same code path as the REST endpoint and the in-process skill).

## Wire-up

Add to `backend/mcp_servers.json`:

```json
{
  "mcpServers": {
    "test_server": { "command": "python", "args": ["dummy_mcp_server.py"], "type": "stdio" },
    "quote_intel": {
      "command": "python",
      "args": ["../mcp-servers/quote-intel-server/server.py"],
      "type": "stdio"
    }
  }
}
```

Then on swarm startup `MCPManager.connect_all()` will spawn the server
and inject its tools into the agent toolset.

## Pipeline at a glance

```
DB (quotes table)
  -> fetch (tenant-scoped, newest first)
  -> mask     [CUST_001] [PHONE_002] [EMAIL_003] [COMPANY_004]
  -> top-N    (amount_weighted_recency | amount_desc | recency)
  -> LLM      (LLMRouter BALANCED tier, tenant-overridden API key honoured)
  -> unmask   (substitute tokens back -> human-facing markdown)
```

## Tenant context

The MCP transport has no HTTP request, so we read tenant from:
1. The `tenant_id` argument in the tool call, if provided
2. The `MCP_TENANT_ID` environment variable
3. Falls back to `"default"`
