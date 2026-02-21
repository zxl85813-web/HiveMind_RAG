"""
Health check endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "ok", "service": "hivemind-rag"}


@router.get("/ready")
async def readiness_check():
    """Readiness check — verifies all dependencies are available."""
    # TODO: Check DB, Redis, Vector Store, LLM connectivity
    return {"status": "ready"}
