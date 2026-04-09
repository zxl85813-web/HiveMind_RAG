"""
Swarm Memory Bridge (M4.2.1)
Integrates the Agent Swarm kernel with the multi-tier memory infrastructure.
- L1/L2/L3 Semantic Memory
- Episodic Memory (Cross-session)
- Reflective Memory (Reflection Logs)
"""

from datetime import datetime
from typing import Any

from loguru import logger

from app.agents.memory import SharedMemoryManager
from app.services.memory.episodic_service import episodic_memory_service
from app.services.memory.memory_service import MemoryService
from app.services.memory.social_graph_service import SocialGraphService, SocializedConsensus


class SwarmMemoryBridge:
    def __init__(self, user_id: str):
        self.user_id = user_id
        # Tiered Memory Strategy (L1-L5)
        self.memory_svc = MemoryService(user_id=user_id)
        # Session Memory (Episodic)
        self.episodic_svc = episodic_memory_service
        # Swarm Shared State (Reflections/TODOs)
        self.shared_mgr = SharedMemoryManager()
        # L5 Socialized Knowledge Graph (Collective Unconsciousness)
        self.social_graph = SocialGraphService()

    async def load_historical_context(self, query: str) -> tuple[str, bool]:
        """
        Recall multi-tier historical context before planning, and assess risk (M4.2.4).
        Returns (context_string, is_high_risk).
        """
        logger.info(f"[SwarmMemory] Loading historical context and assessing risk for: {query}")
        is_high_risk = False
        try:
            # 1. Standard L1-L5 Retrieval
            context = await self.memory_svc.get_context(query)

            # 2. Reflection Log Retrieval
            reflections = await self.shared_mgr.get_reflections(limit=5)
            reflection_context = ""
            directives = []

            for r in reflections:
                # Semantic/Topic Matching
                if any(kw in query.lower() for kw in r.topic.lower().split()) or \
                   any(kw in query.lower() for kw in r.match_key.lower().split()):
                    
                    reflection_context += f"\n- [Past Reflection/{r.signal_type}] {r.summary}"
                    
                    # RISK DETECTION: If past confidence was low or action is pending_todo, it's high risk
                    if r.confidence_score < 0.6 or r.action_taken == "PENDING_TODO":
                        is_high_risk = True

                    # Extract L4 Cognitive Directive
                    directive = r.details.get("analysis", {}).get("cognitive_directive") or r.details.get("directive")
                    if directive:
                        directives.append(directive)

            # 3. L5 Collective Unconsciousness (Subconscious Recall)
            wisdom = await self.social_graph.suggest_prior_wisdom(query)
            wisdom_context = ""
            for item in wisdom:
                wisdom_context += f"\n- [Past Swarm Consensus] Requirement: {item['point']}\n  Solution: {item['solution']}\n  Rationale: {item['rationale']}"

            if wisdom_context:
                context += f"\n\n--- COLLECTIVE INTELLIGENCE FROM PAST DEBATES ---\n{wisdom_context}"

            if reflection_context:
                context += f"\n\n--- RELEVANT PAST REFLECTIONS ---\n{reflection_context}"
            
            if directives:
                directive_block = "\n".join([f"!!! [SYSTEM DIRECTIVE] {d}" for d in directives])
                context += f"\n\n--- HARD CONSTRAINTS FROM PAST FAILURES ---\n{directive_block}\n(You MUST adhere to these directives to pass the L4 Integrity Gate.)"

            return context, is_high_risk
        except Exception as e:
            logger.error(f"Failed to load historical context: {e}")
            return "", False

    async def persist_successful_outcome(self, query: str, context: dict[str, Any], conversation_id: str | None = None):
        """
        Write back the successful swarm outcome to all memory tiers.
        """
        logger.info("📼 [SwarmMemory] Persisting successful outcome to memory.")

        # 1. Summarize the collective intelligence
        outcome_summary = f"[Swarm Execution Success] Outcome for: {query}\n"
        for task_id, output in context.items():
            # Truncate large outputs for memory efficiency
            summary_snippet = str(output)[:500] + ("..." if len(str(output)) > 500 else "")
            outcome_summary += f"- {task_id}: {summary_snippet}\n"

        # 2. Add to L3 Vector (and trigger L1/L2 extraction via density scoring)
        await self.memory_svc.add_memory(
            outcome_summary,
            metadata={
                "source": "swarm_kernel",
                "type": "execution_result",
                "query": query
            }
        )

        # 3. Store as an Episode if in a conversation
        if conversation_id:
            logger.debug(f"Storing swarm episode for conversation: {conversation_id}")
            # Map context to messages for episodic distillation
            simulated_messages = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": outcome_summary}
            ]
            await self.episodic_svc.store_episode(
                user_id=self.user_id,
                conversation_id=conversation_id,
                messages=simulated_messages,
                agent_names=["HVM-Supervisor"]
            )

    async def record_failure_reflection(self, query: str, feedback: str, agent_name: str = "HVM-Reviewer"):
        """
        Log a gap in intelligence/performance to the Reflection Log.
        This enables future planners to avoid similar pitfalls.
        """
        from app.models.agents import ReflectionType
        logger.warning(f"🪞 [SwarmMemory] Recording GAP reflection: {feedback[:100]}")

        entry = ReflectionEntry(
            type=ReflectionType.ERROR_CORRECTION,
            agent_name=agent_name,
            signal_type=ReflectionSignalType.GAP,
            topic="Swarm Execution Failure",
            summary=feedback,
            match_key=f"swarm_fail_{self.user_id}", # Could be more specific based on query hash
            details={
                "query": query,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.shared_mgr.add_reflection(entry)

    async def solidify_swarm_consensus(self, query: str, consensus_plan: str, rationale: str, trace_id: str):
        """
        Elevates a swarm-level consensus to a global architectural pattern in the social graph.
        """
        logger.info(f"[SwarmMemory] Elevating consensus to Collective Wisdom.")
        consensus = SocializedConsensus(
            decision_point=query,
            consensus_summary=consensus_plan,
            rationale=rationale,
            trace_id=trace_id
        )
        await self.social_graph.solidify_consensus(consensus)
