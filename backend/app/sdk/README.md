# `app.sdk` — HiveMind Public SDK Facade

Stable, high-level Python entry points for embedding HiveMind into external
code. Internal modules should keep using the underlying services directly;
this package exists so that **external consumers** (other Python apps,
notebooks, scripts, downstream services) have one import path that won't
break when we refactor the internals.

## What's in here

| Module | Facade for | Purpose |
| ------ | ---------- | ------- |
| `rag.py`   | `app.services.rag_gateway.RAGGateway` | RAG platform: retrieve fragments from one or more KBs with circuit-breaker fault tolerance. |
| `agent.py` | `app.agents.swarm.SwarmOrchestrator`  | Agent platform: register agents, run conversations (`ask`), stream intermediate events (`stream`). |

Top-level exports (`from app.sdk import ...`):
- `HiveMindRAG`, `RAGRetrievalResult`
- `HiveMindSwarm`, `SwarmAnswer`

## Quick start

```python
import asyncio
from app.sdk import HiveMindRAG, HiveMindSwarm

async def main():
    # --- RAG platform ---
    rag = HiveMindRAG()
    result = await rag.retrieve("What is HiveMind?", kb_ids=["default"], top_k=5)
    for f in result.fragments:
        print(f.score, f.kb_id, f.content[:80])

    # --- Agent platform ---
    swarm = HiveMindSwarm()
    swarm.bootstrap_default_agents()           # registers web/code/rag
    answer = await swarm.ask("Summarize the project.")
    print(answer["messages"][-1].content)

    # Streaming variant
    async for event in swarm.stream("Tell me a story"):
        print(event)

asyncio.run(main())
```

## Design rules

1. **Thin layer only.** Facades do not add business logic. If you find
   yourself implementing behaviour here, push it down into a service.
2. **Stable surface.** Public method signatures should change as rarely as
   possible. Breaking changes require an `APP_VERSION` bump and an entry in
   `docs/changelog/`.
3. **Mirror the REST surface.** Method names should track the corresponding
   FastAPI routes so that a future generated HTTP client (see
   [`shared/openapi/`](../../../shared/openapi)) can act as a drop-in
   alternative.
4. **No circular imports.** Facades may import from `app.services` and
   `app.agents`; those layers must NOT import from `app.sdk`.

## Roadmap

- Add `HiveMindKnowledgeBase` for KB CRUD once `services/knowledge/kb_service.py`
  CRUD endpoints are completed (REGISTRY 🔲 → ✅).
- Add `HiveMindMCP` once `MCPManager` exits its current "framework" state.
- Publish as a separately installable package (`hivemind-sdk`) by extracting
  this directory plus its minimum dependencies via the `pyproject.toml`
  workspace work in plan B.
