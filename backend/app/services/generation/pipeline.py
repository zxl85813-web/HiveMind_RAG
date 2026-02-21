"""
Generation Pipeline — Orchestrator for Content Creation.
"""
from typing import List
from .protocol import GenerationContext
from .steps import BaseGenerationStep, ContextRetrievalStep, DraftingStep, SelfCorrectionStep, ExcelExportStep

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
        self.steps: List[BaseGenerationStep] = [
            ContextRetrievalStep(),
            DraftingStep(),
            SelfCorrectionStep(),
            ExcelExportStep()
        ]

    async def run(self, task_description: str, kb_ids: List[str]) -> GenerationContext:
        """
        Execute the generation pipeline.
        """
        ctx = GenerationContext(
            task_description=task_description,
            kb_ids=kb_ids
        )
        
        for step in self.steps:
            try:
                await step.execute(ctx)
            except Exception as e:
                ctx.log("Pipeline", f"Error in step {step.__class__.__name__}: {e}")
                
        return ctx

_pipeline = GenerationPipeline()
def get_generation_service() -> GenerationPipeline:
    return _pipeline
