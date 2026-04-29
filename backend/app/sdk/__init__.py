"""
HiveMind Public SDK
===================

High-level facades for embedding HiveMind into external Python code without
having to navigate the full ``app.services`` / ``app.agents`` internals.

Two facades are exposed:

* :class:`HiveMindRAG`  — knowledge retrieval (wraps ``RAGGateway``)
* :class:`HiveMindSwarm` — agent orchestration (wraps ``SwarmOrchestrator``)

Quick start::

    import asyncio
    from app.sdk import HiveMindRAG, HiveMindSwarm

    async def main():
        rag = HiveMindRAG()
        result = await rag.retrieve("What is HiveMind?", kb_ids=["default"])
        print(result.fragments)

        swarm = HiveMindSwarm()
        await swarm.bootstrap_default_agents()
        answer = await swarm.ask("Summarize the project.")
        print(answer["messages"][-1].content)

    asyncio.run(main())

These facades are intentionally thin — they don't add new behaviour, they
just give external callers a single, stable import path. Internal modules
should keep using the underlying services directly.
"""

from app.sdk.rag import HiveMindRAG, RAGRetrievalResult
from app.sdk.agent import HiveMindSwarm, SwarmAnswer

__all__ = [
    "HiveMindRAG",
    "RAGRetrievalResult",
    "HiveMindSwarm",
    "SwarmAnswer",
]
