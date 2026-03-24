"""
API Router — aggregates all route modules.
"""

from fastapi import APIRouter

from app.api.routes import (
    agents,
    audit,
    audit_v3,
    chat,
    evaluation,
    finetuning,
    generation,
    health,
    knowledge,
    learning,
    memory,
    observability,
    pipelines,
    security,
    settings,
    tags,
    telemetry,
    websocket,
)

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(telemetry.router, tags=["Telemetry"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
router.include_router(learning.router, prefix="/learning", tags=["External Learning"])
router.include_router(generation.router, prefix="/generation", tags=["Generation"])
router.include_router(memory.router, prefix="/memory", tags=["Memory"])
router.include_router(tags.router, prefix="/tags", tags=["Knowledge Tags"])
router.include_router(security.router, prefix="/security", tags=["Security & Desensitization"])
router.include_router(audit.router, prefix="/audit", tags=["Data Quality Audit"])
router.include_router(audit_v3.router, prefix="/audit/v3", tags=["V3 Swarm Audit"])
router.include_router(evaluation.router, prefix="/evaluation", tags=["RAG Evaluation"])
router.include_router(finetuning.router, prefix="/finetuning", tags=["Fine-tuning SFT Data"])
router.include_router(pipelines.router, prefix="/pipelines", tags=["Pipelines"])
router.include_router(settings.router, prefix="/settings", tags=["Platform Settings"])
router.include_router(observability.router, prefix="/observability", tags=["Observability"])
