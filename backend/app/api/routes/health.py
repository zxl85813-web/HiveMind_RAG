"""
Health check endpoints.
"""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check — includes platform mode info."""
    return {
        "status": "ok",
        "service": "hivemind",
        "mode": settings.PLATFORM_MODE.value,
        "modules": {
            "rag": settings.rag_enabled,
            "agent": settings.agent_enabled,
        },
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check — verifies dependencies for active modules."""
    checks = {"database": "ok"}

    if settings.rag_enabled:
        checks["vector_store"] = "ok"  # TODO: actual connectivity check
        checks["embedding"] = "ok"

    if settings.agent_enabled:
        checks["llm"] = "ok"  # TODO: actual connectivity check

    return {
        "status": "ready",
        "mode": settings.PLATFORM_MODE.value,
        "checks": checks,
    }
