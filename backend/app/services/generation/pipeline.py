"""
Generation Pipeline — Orchestrator for Content Creation.
"""

from .protocol import GenerationContext
from .steps import BaseGenerationStep, ContextRetrievalStep, DraftingStep, ExcelExportStep, SelfCorrectionStep
from app.core.logging import get_trace_logger

logger = get_trace_logger(__name__)


class GenerationPipeline:
    """
    Standard Generation Pipeline.
    Steps:
    1. Retrieval (Get context)
    2. Active Creating (LLM Draft)
    3. Self-Correction (LLM Review)
    4. Export (Excel/CSV)
    """

    def __init__(self):
        self.steps: list[BaseGenerationStep] = [
            ContextRetrievalStep(),
            DraftingStep(),
            SelfCorrectionStep(),
            ExcelExportStep(),
        ]

    async def run(self, task_description: str, kb_ids: list[str], user_id: str = "default_user", ctx: GenerationContext | None = None) -> GenerationContext:
        """
        Execute the generation pipeline.
        """
        logger.info(f"🚀 Starting generation pipeline for task: {task_description[:30]}...")
        if not ctx:
            ctx = GenerationContext(task_description=task_description, kb_ids=kb_ids, user_id=user_id)

        for step in self.steps:
            try:
                logger.info(f"⏳ Executing step: {step.__class__.__name__}")
                await step.execute(ctx)
            except Exception as e:
                logger.error(f"❌ Error in step {step.__class__.__name__}: {e}")
                ctx.log("Pipeline", f"Error in step {step.__class__.__name__}: {e}")

        return ctx


_pipeline = GenerationPipeline()


def get_generation_service() -> GenerationPipeline:
    return _pipeline
