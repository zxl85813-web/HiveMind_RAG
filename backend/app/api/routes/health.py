"""
Health check endpoints.
"""

from fastapi import APIRouter
from app.common.response import ApiResponse

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def health_check():
    """Basic health check."""
    return ApiResponse.ok(data={"status": "ok", "service": "hivemind-rag"})


@router.get("/ready", response_model=ApiResponse)
async def readiness_check():
    """Readiness check — verifies all dependencies are available."""
    # TODO: Check DB, Redis, Vector Store, LLM connectivity
    return ApiResponse.ok(data={"status": "ready"})
