# HiveMind delivery blueprints

A *blueprint* is a single YAML/JSON file that describes one customer delivery package
(name, platform mode, UI mode, agents, skills, MCP servers, env overrides).

The export pipeline turns a blueprint into a self-contained directory (or `.zip`)
that the customer can `docker compose up -d` on their intranet.

## Quick start

```bash
# Validate
python scripts/export_blueprint.py blueprints/quote-bot.example.yaml --dry-run

# Export
python scripts/export_blueprint.py blueprints/quote-bot.example.yaml \
    --output dist/quote-bot --zip --overwrite

# Discover what assets you can reference
python scripts/export_blueprint.py --list-assets
```

## File layout of an output package

```
dist/<name>/
  README_DEPLOY.md          ← auto-generated 5-step deploy guide
  docker-compose.yml        ← pruned for the chosen platform_mode
  .env.example              ← LLM keys, postgres password, env_overrides
  blueprint.lock.yaml       ← frozen spec used to generate this package
  blueprint.lock.json       ← same, machine-friendly
  backend/                  ← FastAPI app (pruned: no tests/debug)
  frontend_dist/            ← optional, present iff `frontend/dist/` was built
  skills/<name>/            ← only the skills referenced by the blueprint
  mcp-servers/<name>/       ← only the MCP servers referenced
```

## Schema

See [`scripts/_export/schema.py`](../scripts/_export/schema.py) for the authoritative
pydantic model. Every field has a `description` attribute consumed by the UI wizard.
