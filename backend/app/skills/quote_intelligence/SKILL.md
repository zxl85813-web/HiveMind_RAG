---
name: quote-intelligence
description: |
  End-to-end sales-quote analysis with reversible PII masking.
  Use when the user asks to "analyse / summarise / review recent quotes",
  "find top deals", or wants a sales-intel report. The skill fetches
  recent quotes from the database, masks customer PII (name / phone /
  email / company) into opaque tokens, picks the top-N via a configurable
  ranking algorithm, ships only the masked payload to the LLM, then
  re-fills the original PII back into the LLM's markdown report so the
  human reader sees real names while the LLM only ever saw tokens.
version: 0.1.0
tags: [sales, analytics, pii-safe, mcp]
---

# Quote Intelligence Skill

## When to use

Trigger this skill whenever the user wants:

- A summary of recent **sales quotes** / **deals** / **opportunities**
- A ranked list of "top N" customers / opportunities
- A markdown sales-intel report suitable for forwarding internally

## Why masking matters

Customer names, phones, and emails are PII. We never send them to a
third-party LLM. The skill instead:

1. Replaces each unique value with a stable token like `[CUST_001]`,
   `[PHONE_002]`, `[EMAIL_003]`, `[COMPANY_004]`.
2. Sends *only* the masked records to the LLM.
3. After the LLM returns its markdown report (which references the
   tokens verbatim), the skill swaps each token back to the original
   value before the report is shown to the human.

## Tools (Tier 3)

| Tool                          | Purpose                                       |
|-------------------------------|-----------------------------------------------|
| `quote_intel_run`             | One-shot pipeline: fetch -> mask -> top-N -> LLM -> unmask |
| `quote_intel_fetch_masked`    | Fetch + mask only (returns masked records + vault id) |

## Recommended ranking strategies

- `amount_weighted_recency` *(default)* — high-value deals decayed by age (30d half-life)
- `amount_desc` — pure sort by deal size
- `recency` — newest first

## MCP exposure

The same pipeline is also exposed via the `quote-intel-server` MCP
server (see `mcp-servers/quote-intel-server/`). When that MCP server is
configured in `backend/mcp_servers.json`, an external agent can call the
pipeline through standard MCP tools rather than this in-process skill.
