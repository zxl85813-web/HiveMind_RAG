
from datetime import datetime
from typing import Any
from loguru import logger
from sqlmodel import select

from app.core.database import async_session_factory
from app.models.agents import ReflectionEntry, ReflectionType, ReflectionSignalType, TodoItem, TodoPriority, TodoStatus
from app.models.evaluation import BadCase
from app.services.llm_gateway import llm_gateway

class SelfLearningService:
    """
    L4 Autonomous Evolution Service (Agentic Self-Learning).
    Handles 'Wrong Case' reflection and automatic system improvement suggestions.
    """

    async def record_bad_case(
        self, 
        question: str, 
        bad_answer: str, 
        ground_truth: str, 
        reason: str = "l3_eval_failure",
        metadata: dict[str, Any] = None
    ) -> BadCase:
        """Record a failure event for future reflection."""
        async with async_session_factory() as session:
            case = BadCase(
                question=question,
                bad_answer=bad_answer,
                expected_answer=ground_truth,
                reason=reason,
                status="pending"
            )
            session.add(case)
            await session.commit()
            await session.refresh(case)
            logger.info(f"🚨 [L4 Self-Learning] Recorded Bad Case: {case.id}")
            return case

    async def trigger_autonomous_reflection(self, case_id: str):
        """Perform agentic reflection on a specific bad case."""
        async with async_session_factory() as session:
            case = await session.get(BadCase, case_id)
            if not case:
                return

            logger.info(f"🧠 [L4 Self-Learning] Triggering autonomous reflection for case {case_id}...")

            # 1. Analyze the root cause using the Critic Agent logic
            prompt = f"""
            ### FAILURE ANALYSIS REQUEST (L4 EVOLUTION)
            The HiveMind Swarm failed a quality gate. Analyze the discrepancy:
            
            Question: {case.question}
            Produced Answer: {case.bad_answer}
            Target (Ground Truth): {case.expected_answer}
            
            Identify the ROOT CAUSE from these categories:
            - RETRIEVAL_GAP: The necessary facts were not present in the RAG context.
            - REASONING_ERROR: The facts were present, but the agent failed to connect them.
            - PROTOCOL_VIOLATION: The agent ignored safety or formatting constraints.
            - NOISE_INTERFERENCE: Irrelevant context distracted the agent.
            
            Output JSON:
            {{
              "root_cause": "CATEGORY",
              "explanation": "Detailed analysis of why it failed",
              "suggested_fix": "Specific action to prevent this",
              "cognitive_directive": "A short, mandatory imperative instruction (e.g., 'DO NOT proceed if research is empty', 'MANDATE peer-review for X')",
              "confidence": 0.0-1.0
            }}
            """
            
            response = await llm_gateway.call_tier(
                tier=3,
                prompt=prompt,
                system_prompt="You are the HVM-Evolution-Critic. Your goal is to turn failures into UNBREAKABLE rules for the AI Swarm.",
                response_format={"type": "json_object"}
            )

            import json
            try:
                analysis = json.loads(response.content)
                
                # 2. Store reflection entry
                reflection = ReflectionEntry(
                    type=ReflectionType.ERROR_CORRECTION,
                    signal_type=ReflectionSignalType.ISSUE,
                    agent_name="EvolutionCritic",
                    topic="L3_Eval_Failure",
                    match_key=case.question[:50],
                    summary=f"Failure Root Cause: {analysis.get('root_cause')}",
                    details={
                        "case_id": case_id,
                        "analysis": analysis,
                        "metadata": case.reason
                    },
                    confidence_score=analysis.get("confidence", 0.5),
                    action_taken="PENDING_TODO"
                )
                session.add(reflection)
                
                # 3. Create active Todo for improvement
                todo = TodoItem(
                    title=f"Evolution Fix: Resolve {analysis.get('root_cause')} for '{case.question[:30]}...'",
                    description=f"Analysis: {analysis.get('explanation')}\n\nSuggested Fix: {analysis.get('suggested_fix')}",
                    priority=TodoPriority.HIGH,
                    status=TodoStatus.PENDING,
                    created_by="EvolutionCritic"
                )
                session.add(todo)
                
                case.status = "reviewed"
                await session.commit()
                
                logger.info(f"✅ [L4 Self-Learning] Reflection complete. Created Todo for {analysis.get('root_cause')}")
                
            except Exception as e:
                logger.error(f"Failed to process evolution reflection: {e}")

self_learning_service = SelfLearningService()
