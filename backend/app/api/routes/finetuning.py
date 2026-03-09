"""
Fine-tuning API — Manage SFT dataset items.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.common.response import ApiResponse
from app.models.finetuning import FineTuningItem

router = APIRouter()


class FineTuningCreate(BaseModel):
    instruction: str
    output: str
    input_context: str = ""
    kb_id: str = ""
    source_type: str = "manual"
    source_id: str = ""


@router.post("/items", response_model=ApiResponse[FineTuningItem])
async def create_item(data: FineTuningCreate, db: AsyncSession = Depends(deps.get_db)):
    item = FineTuningItem(**data.dict())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ApiResponse.ok(data=item)


@router.get("/items", response_model=ApiResponse[list[FineTuningItem]])
async def list_items(db: AsyncSession = Depends(deps.get_db)):
    from sqlmodel import select

    res = await db.execute(select(FineTuningItem))
    return ApiResponse.ok(data=res.scalars().all())


@router.delete("/items/{item_id}", response_model=ApiResponse[None])
async def delete_item(item_id: str, db: AsyncSession = Depends(deps.get_db)):
    item = await db.get(FineTuningItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return ApiResponse.ok(message="Item deleted")
