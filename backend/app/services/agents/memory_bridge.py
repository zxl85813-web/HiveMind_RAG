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
from sqlmodel import select

from app.agents.memory import SharedMemoryManager
from app.services.memory.episodic_service import episodic_memory_service
from app.services.memory.memory_service import MemoryService
from app.services.memory.social_graph_service import SocialGraphService, SocializedConsensus
from app.models.evolution import CognitiveDirective


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
        context = ""
        directives = []

        # 1. Consolidated L4 Evolutionary Directives (M4.2.5) - HIGH PRIORITY
        try:
            stmt = select(CognitiveDirective).where(CognitiveDirective.is_active == True)
            from app.core.database import async_session_factory
            async with async_session_factory() as session:
                res = await session.execute(stmt)
                consolidated = res.scalars().all()
                for cd in consolidated:
                    directives.append(f"{cd.directive} (Ref: L4-EVO-v{cd.version})")
        except Exception as e:
            logger.error(f"Failed to load consolidated directives: {e}")

        try:
            # 2. Standard L1-L5 Retrieval (Vector/Text)
            try:
                context = await self.memory_svc.get_context(query)
            except Exception as e:
                logger.warning(f"Memory search failed: {e}")
                context = ""

            # 3. Reflection Log Retrieval (M9.1.3: 向量语义匹配 + 关键词兜底)
            reflection_context = ""
            try:
                reflections = await self.shared_mgr.get_reflections(limit=10)

                # 尝试用向量语义匹配（如果 MemoryService 可用）
                matched_reflections = []
                try:
                    # 用 MemoryService 做语义搜索，找到与 query 语义相关的反思
                    semantic_results = await self.memory_svc.search(query, top_k=5)
                    semantic_keywords = set()
                    for sr in semantic_results:
                        # 提取语义搜索结果中的关键词
                        content = sr.get("content", "") if isinstance(sr, dict) else str(sr)
                        semantic_keywords.update(w.lower() for w in content.split() if len(w) > 3)
                except Exception:
                    semantic_keywords = set()

                for r in reflections:
                    # 方式 1: 原始关键词匹配
                    keyword_match = (
                        any(kw in query.lower() for kw in (r.topic or "").lower().split()) or
                        any(kw in query.lower() for kw in (r.match_key or "").lower().split())
                    )
                    # 方式 2: 语义关键词交叉匹配（M9.1.3 新增）
                    semantic_match = False
                    if semantic_keywords:
                        r_words = set(w.lower() for w in (r.summary or "").split() if len(w) > 3)
                        semantic_match = len(r_words & semantic_keywords) >= 2

                    if keyword_match or semantic_match:
                        matched_reflections.append(r)
                        reflection_context += f"\n- [Past Reflection/{r.signal_type}] {r.summary}"
                        if r.confidence_score < 0.6 or r.action_taken == "PENDING_TODO":
                            is_high_risk = True

                        directive = r.details.get("analysis", {}).get("cognitive_directive") or r.details.get("directive")
                        if directive:
                            directives.append(directive)

                if matched_reflections:
                    logger.info(f"[SwarmMemory] Matched {len(matched_reflections)} reflections (keyword+semantic)")
            except Exception as e:
                logger.warning(f"Reflection lookup failed: {e}")

            # 4. L5 Collective Unconsciousness (Subconscious Recall)
            try:
                wisdom = await self.social_graph.suggest_prior_wisdom(query)
                wisdom_context = ""
                for item in wisdom:
                    wisdom_context += f"\n- [Past Swarm Consensus] Requirement: {item['point']}\n  Solution: {item['solution']}\n  Rationale: {item['rationale']}"
                if wisdom_context:
                    context += f"\n\n--- COLLECTIVE INTELLIGENCE FROM PAST DEBATES ---\n{wisdom_context}"
            except Exception as e:
                logger.warning(f"Social graph recall failed: {e}")

            if reflection_context:
                context += f"\n\n--- RELEVANT PAST REFLECTIONS ---\n{reflection_context}"
            
            if directives:
                # Remove duplicates
                unique_directives = list(dict.fromkeys(directives))
                directive_block = "\n".join([f"!!! [SYSTEM DIRECTIVE] {d}" for d in unique_directives])
                context += f"\n\n--- HARD CONSTRAINTS FROM PAST FAILURES ---\n{directive_block}\n(You MUST adhere to these directives to pass the L4 Integrity Gate.)"

            return context, is_high_risk
        except Exception as e:
            logger.error(f"Failed to assemble historical context: {e}")
            return context, False

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
