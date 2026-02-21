"""
Generation API Endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from app.services.generation import get_generation_service
from app.services.generation.protocol import GenerationContext

router = APIRouter()

class GenerateRequest(BaseModel):
    task_description: str
    kb_ids: List[str]

class GenerateResponse(BaseModel):
    status: str
    message: str
    artifact_path: Optional[str] = None
    step_logs: List[str] = []
    draft: Optional[Dict[str, Any]] = None

@router.post("/run", response_model=GenerateResponse)
async def run_generation(request: GenerateRequest):
    """
    Run the Generation Pipeline (Retrieval -> Draft -> Correct -> Export).
    """
    service = get_generation_service()
    try:
        ctx: GenerationContext = await service.run(
            task_description=request.task_description,
            kb_ids=request.kb_ids
        )
        
        # Convert internal DraftResult to Dict
        draft_dict = None
        if ctx.draft_content:
            draft_dict = ctx.draft_content.model_dump()
            
        return GenerateResponse(
            status="completed",
            message="Generation successful",
            artifact_path=ctx.final_artifact_path,
            step_logs=ctx.feedback_log,
            draft=draft_dict
        )
    except Exception as e:
        # In production, log error properly
        raise HTTPException(status_code=500, detail=str(e))
