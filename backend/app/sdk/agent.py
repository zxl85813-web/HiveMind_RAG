"""
HiveMindSwarm — the public facade for the Agent platform capability.

Wraps :class:`app.agents.swarm.SwarmOrchestrator` so external callers can
spin up the swarm, register agents, and run conversations without touching
LangGraph state details directly::

    from app.sdk import HiveMindSwarm

    swarm = HiveMindSwarm()
    await swarm.bootstrap_default_agents()      # registers web/code/rag/...
    final_state = await swarm.ask("Hello")
    async for event in swarm.stream("Tell me a story"):
        ...

The facade does NOT alter swarm behaviour — it just gives external callers a
single import path and a couple of convenience helpers.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Sequence

from app.agents.swarm import AgentDefinition, SwarmOrchestrator

# Re-export the canonical state dict under a friendlier SDK name.
SwarmAnswer = dict[str, Any]


# Default agent roster mirrors the bootstrap in app/main.py lifespan, so that
# external callers get the same out-of-the-box behaviour as the FastAPI app.
_DEFAULT_AGENTS: tuple[AgentDefinition, ...] = (
    AgentDefinition(
        name="web",
        description="Able to search the internet for the most up-to-date information.",
        model_hint="fast",
    ),
    AgentDefinition(
        name="code",
        description="Specialized in writing, debugging, and explaining code in various programming languages.",
        model_hint="reasoning",
    ),
    AgentDefinition(
        name="rag",
        description="Knowledge Expert. Use this for ANY factual questions, knowledge base lookups, or internal documentation queries.",
        model_hint="balanced",
    ),
)


class HiveMindSwarm:
    """High-level entry point for multi-agent orchestration."""

    def __init__(self, orchestrator: SwarmOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator or SwarmOrchestrator()

    # ── Agent management ────────────────────────────────────
    def register_agent(self, agent: AgentDefinition) -> None:
        """Register a custom agent into the swarm."""
        self._orchestrator.register_agent(agent)

    def list_agents(self) -> list[AgentDefinition]:
        return self._orchestrator.list_agents()

    def bootstrap_default_agents(self, extra: Sequence[AgentDefinition] = ()) -> None:
        """Register the standard ``web`` / ``code`` / ``rag`` agents.

        Use this when you want a usable swarm with one call. Extra agents can
        be passed in to be registered alongside the defaults.
        """
        for agent in (*_DEFAULT_AGENTS, *extra):
            self._orchestrator.register_agent(agent)

    # ── Conversation API ────────────────────────────────────
    async def ask(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        conversation_id: str = "sdk_default",
    ) -> SwarmAnswer:
        """Run a single request through the swarm and return the final state.

        The returned dict includes ``messages`` (the LangChain message log),
        ``agent_outputs``, ``retrieval_trace`` and other swarm telemetry.
        """
        return await self._orchestrator.invoke(
            user_message=message,
            context=context,
            conversation_id=conversation_id,
        )

    async def stream(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        conversation_id: str = "sdk_stream",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream intermediate node updates from the swarm graph."""
        async for event in self._orchestrator.invoke_stream(
            user_message=message,
            context=context,
            conversation_id=conversation_id,
        ):
            yield event

    @property
    def orchestrator(self) -> SwarmOrchestrator:
        """Escape hatch for advanced callers that need the raw orchestrator."""
        return self._orchestrator
