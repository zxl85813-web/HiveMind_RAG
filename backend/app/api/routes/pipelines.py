from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.models.pipeline_config import PipelineConfig
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

class PipelineConfigRequest(BaseModel):
    name: str
    description: str = ""
    pipeline_type: str = "ingestion"
    flow_data_json: str
    execution_sequence_json: str = "[]"

@router.get("", response_model=List[PipelineConfig])
async def list_pipelines(session: AsyncSession = Depends(get_db_session)):
    stmt = select(PipelineConfig)
    result = await session.exec(stmt)
    return result.all()

@router.post("", response_model=PipelineConfig)
async def create_pipeline(req: PipelineConfigRequest, session: AsyncSession = Depends(get_db_session)):
    cfg = PipelineConfig(**req.model_dump())
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return cfg

@router.put("/{pipeline_id}", response_model=PipelineConfig)
async def update_pipeline(pipeline_id: str, req: PipelineConfigRequest, session: AsyncSession = Depends(get_db_session)):
    stmt = select(PipelineConfig).where(PipelineConfig.id == pipeline_id)
    res = await session.exec(stmt)
    cfg = res.first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Pipeline info not found")
    
    for k, v in req.model_dump().items():
        setattr(cfg, k, v)
    
    await session.commit()
    await session.refresh(cfg)
    return cfg

@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, session: AsyncSession = Depends(get_db_session)):
    stmt = select(PipelineConfig).where(PipelineConfig.id == pipeline_id)
    res = await session.exec(stmt)
    cfg = res.first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Not found")
    await session.delete(cfg)
    await session.commit()
    return {"status": "ok"}
