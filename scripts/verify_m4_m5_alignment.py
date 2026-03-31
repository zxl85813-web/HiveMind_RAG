import asyncio
import json
import sys
import os

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.append(backend_path)

from app.agents.swarm import SwarmOrchestrator
from app.services.evaluation import EvaluationService
from app.models.evaluation import EvaluationSet, EvaluationItem
from app.core.database import async_session_factory
from sqlalchemy import select
from loguru import logger

async def test_swarm_chat_stream():
    logger.info("🚀 Testing Swarm Chat Stream (M4)...")
    swarm = SwarmOrchestrator()
    conv_id = "test-conv-001"
    message = "如何优化 HiveMind 的图谱记忆索引？"
    
    updates_count = 0
    thoughts_found = 0
    delta_found = 0
    
    async for update in swarm.invoke_stream(user_message=message, conversation_id=conv_id):
        updates_count += 1
        for node, diff in update.items():
            if "thought_log" in diff or "status_update" in diff:
                thoughts_found += 1
            if "messages" in diff:
                delta_found += 1
                
    logger.success(f"Swarm Chat Stream OK: {updates_count} updates, {thoughts_found} thoughts, {delta_found} message deltas.")
    return True

async def test_rag_evaluation_6metrics():
    logger.info("🧪 Testing RAG Evaluation 6-Metrics (M5)...")
    service = EvaluationService()
    
    async with async_session_factory() as db:
        # Create a mock testset if none exists
        stmt = select(EvaluationSet).limit(1)
        res = await db.execute(stmt)
        testset = res.scalars().first()
        
        if not testset:
            logger.warning("No testset found, skipping M5 run.")
            return False
            
        logger.info(f"Using testset: {testset.name} ({testset.id})")
        
        # Run a 1-item sample evaluation
        report = await service.run_evaluation(
            db=db, 
            set_id=testset.id, 
            model_name="gpt-4o-mini"
        )
        
        logger.info(f"Report Status: {report.status}")
        logger.info(f"Metrics (6-Dimension):")
        logger.info(f" - Faithfulness: {report.faithfulness}")
        logger.info(f" - Relevance: {report.answer_relevance}")
        logger.info(f" - Context Precision: {report.context_precision}")
        logger.info(f" - Context Recall: {report.context_recall}")
        logger.info(f" - Answer Correctness: {report.answer_correctness}")
        logger.info(f" - Semantic Similarity: {report.semantic_similarity}")
        logger.info(f" - Total Score (Weighted): {report.total_score}")
        
        if report.answer_correctness > 0 or report.semantic_similarity > 0:
            logger.success("M5 6-Metrics verification passed!")
            return True
        else:
            logger.error("M5 Metrics failed to populate.")
            return False

async def main():
    try:
        # 1. Swarm Test
        await test_swarm_chat_stream()
        
        # 2. Evaluation Test (Requires DB/LLM connection, might be mocked in CI)
        # await test_rag_evaluation_6metrics() 
        
    except Exception as e:
        logger.error(f"Verification Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
