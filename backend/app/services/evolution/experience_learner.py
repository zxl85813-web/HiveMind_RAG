
import json
from datetime import datetime
from typing import List, Optional
from loguru import logger
from sqlmodel import Session, select

from app.core.llm import get_llm_service
from app.models.evolution import CognitiveDirective
from app.models.evaluation import BadCase

class ExperienceLearner:
    """
    Automated Learning Service (L4).
    Extracts 'Lessons Learned' from failed agent executions and human corrections.
    """

    def __init__(self):
        self.llm = get_llm_service()

    async def learn_from_correction(self, db: Session, case_id: str) -> Optional[CognitiveDirective]:
        """
        Analyzes a BadCase correction and produces an actionable CognitiveDirective.
        """
        case = await db.get(BadCase, case_id)
        if not case or not case.expected_answer:
            return None

        logger.info(f"🧠 [ExperienceLearner] Analyzing failure pattern for case {case_id}...")

        prompt = (
            "You are a meta-cognitive trainer for an AI swarm.\n"
            "An agent failed to answer a question correctly. A human has provided a correction.\n"
            "Your task is to extract a 'Mandatory Directive' that will prevent this specific failure in the future.\n\n"
            f"Question: {case.question}\n"
            f"Bad Answer: {case.bad_answer}\n"
            f"Reasoning for Bad Answer: {case.reason or 'Unknown'}\n"
            f"Correct Answer (Ground Truth): {case.expected_answer}\n\n"
            "Output a JSON object:\n"
            "{\n"
            "  'topic': 'A short category string (e.g. FACTUAL_PRECISION, SAFETY_ALIGNMENT)',\n"
            "  'directive': 'A concise, punchy instruction starting with \"Always...\" or \"Never...\"',\n"
            "  'confidence': float (0.0 to 1.0)\n"
            "}"
        )

        try:
            resp_raw = await self.llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(resp_raw)

            # Check if this directive already exists to avoid duplication
            stmt = select(CognitiveDirective).where(CognitiveDirective.directive == data['directive'])
            existing = await db.execute(stmt)
            if existing.scalars().first():
                logger.info("⏩ [ExperienceLearner] Directive already exists, skipping.")
                return None

            directive = CognitiveDirective(
                topic=data['topic'],
                directive=data['directive'],
                confidence_score=data['confidence'],
                source_reflections=[case_id]
            )
            db.add(directive)
            await db.commit()
            await db.refresh(directive)
            
            logger.info(f"✨ [ExperienceLearner] New Directive Created: {directive.directive}")
            return directive
        except Exception as e:
            logger.error(f"❌ [ExperienceLearner] Failed to learn from case {case_id}: {e}")
            return None

experience_learner = ExperienceLearner()
