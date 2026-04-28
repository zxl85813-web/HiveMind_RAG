
import asyncio
import json
from loguru import logger
from sqlmodel import select, desc
from app.core.database import async_session_factory
from app.models.agents import ReflectionEntry, ReflectionSignalType
from app.models.evolution import CognitiveDirective
from app.services.llm_gateway import llm_gateway

class KnowledgeDistiller:
    """
    Cognitive Distiller (M4.2.5).
    Abstracts specific failures into generalized, stable system rules.
    """

    async def distill_latest_reflections(self, topic_filter: str | None = None) -> int:
        """
        Gathers pending reflections, groups them, and distill into CognitiveDirectives.
        """
        logger.info(f"🔮 [KnowledgeDistiller] Starting distillation cycle...")
        
        async with async_session_factory() as session:
            # 1. Fetch pending reflections that haven't been distilled yet
            # For simplicity, we filter by action_taken="PENDING_TODO"
            statement = select(ReflectionEntry).where(
                ReflectionEntry.signal_type == ReflectionSignalType.ISSUE,
                ReflectionEntry.action_taken == "PENDING_TODO"
            )
            if topic_filter:
                statement = statement.where(ReflectionEntry.topic == topic_filter)
            
            result = await session.execute(statement)
            reflections = result.scalars().all()
            
            if not reflections:
                logger.info("No pending reflections to distill.")
                return 0

            logger.info(f"Found {len(reflections)} reflections for distillation.")

            # 2. Group by topic (heuristic)
            groups = {}
            for r in reflections:
                topic = r.topic or "GENERAL"
                groups.setdefault(topic, []).append(r)

            distilled_count = 0
            for topic, r_list in groups.items():
                logger.info(f"Distilling group: {topic} ({len(r_list)} items)")
                
                # Construct data for LLM
                reflection_data = [
                    {
                        "summary": r.summary,
                        "analysis": r.details.get("analysis", {}),
                        "id": r.id
                    } for r in r_list
                ]

                # 3. Call LLM to consolidate
                prompt = f"""
                ### SYSTEM ARCHITECT DISTILLATION (L4 EVOLUTION)
                You are consolidating multiple AI Swarm failures into a single, unbreakable System Rule.
                
                TOPIC: {topic}
                PAST FAILURES:
                {json.dumps(reflection_data, ensure_ascii=False, indent=2)}
                
                INSTRUCTIONS:
                1. Identify common patterns across these failures.
                2. Formulate a 'Stable Cognitive Directive' - a clear, imperative instruction that prevents these specific errors.
                3. The instruction should be general enough to apply to similar future tasks, but specific enough to be enforceable.
                
                LOGIC:
                - If 'Research failing to find info' is common -> 'Must verify knowledge base health before claim'.
                - If 'Reviewer too soft' is common -> 'MANDATE identifying 3 vulnerabilities'.
                
                OUTPUT JSON:
                {{
                  "directive": "THE_IMP_INSTRUCTION",
                  "confidence": 0.0-1.0,
                  "rationale": "Why this directive was formulated"
                }}
                """

                res = await llm_gateway.call_tier(
                    tier=3,
                    prompt=prompt,
                    system_prompt="You are the HiveMind Chief Evolutionary Architect.",
                    response_format={"type": "json_object"}
                )

                try:
                    data = json.loads(res.content)
                    
                    # 4. Save/Update Directive
                    # Check if a directive for this topic already exists
                    stmt = select(CognitiveDirective).where(CognitiveDirective.topic == topic, CognitiveDirective.is_active == True)
                    existing_res = await session.execute(stmt)
                    existing = existing_res.scalar_one_or_none()
                    
                    if existing:
                        # Evolute the existing directive
                        existing.directive = data["directive"]
                        existing.confidence_score = (existing.confidence_score + data["confidence"]) / 2
                        existing.source_reflections = list(set(existing.source_reflections + [r.id for r in r_list]))
                        existing.version += 1
                        existing.updated_at = datetime.utcnow()
                        session.add(existing)
                    else:
                        new_directive = CognitiveDirective(
                            topic=topic,
                            directive=data["directive"],
                            confidence_score=data["confidence"],
                            source_reflections=[r.id for r in r_list]
                        )
                        session.add(new_directive)
                    
                    # 5. Mark reflections as processed
                    for r in r_list:
                        r.action_taken = f"DISTILLED_INTO_DIRECTIVE_v{existing.version if existing else 1}"
                        session.add(r)
                    
                    await session.commit()
                    distilled_count += 1
                    logger.success(f"✅ Distilled directive for {topic}")

                    # 🛡️ M9.1.1: 自动转化为 HarnessPolicy 图谱节点
                    try:
                        from app.sdk.harness.graph_integration import directive_to_harness_policy

                        directive_obj = existing if existing else new_directive
                        asyncio.create_task(directive_to_harness_policy(
                            directive_id=directive_obj.id,
                            topic=topic,
                            directive_text=data["directive"],
                            confidence=data.get("confidence", 0.0),
                        ))
                    except Exception as graph_exc:
                        logger.debug(f"HarnessPolicy graph write skipped: {graph_exc}")
                    
                except Exception as e:
                    logger.error(f"Failed to distill group {topic}: {e}")
            
            return distilled_count

knowledge_distiller = KnowledgeDistiller()
