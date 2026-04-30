"""
API Router — aggregates all route modules based on PLATFORM_MODE.

Module Classification:
  - CORE:  Always loaded (health, chat, settings, websocket)
  - RAG:   Loaded when rag_enabled (knowledge, learning, evaluation, ingestion, etc.)
  - AGENT: Loaded when agent_enabled (agents, skills, MCP, etc.)
  - SHARED: Loaded in any mode (memory, security, audit, tags)
"""

from fastapi import APIRouter
from loguru import logger

from app.core.config import settings

router = APIRouter()

# ── CORE: Always available ──────────────────────────────────
from app.api.routes import health, chat, websocket, settings as settings_routes, tenants

router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
router.include_router(settings_routes.router, prefix="/settings", tags=["Platform Settings"])
router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])

# ── SHARED: Available in all modes ──────────────────────────
from app.api.routes import memory, tags, security, audit, audit_v3, export

router.include_router(memory.router, prefix="/memory", tags=["Memory"])
router.include_router(tags.router, prefix="/tags", tags=["Knowledge Tags"])
router.include_router(security.router, prefix="/security", tags=["Security & Desensitization"])
router.include_router(audit.router, prefix="/audit", tags=["Data Quality Audit"])
router.include_router(audit_v3.router, prefix="/audit/v3", tags=["V3 Swarm Audit"])
router.include_router(export.router, prefix="/export", tags=["Blueprint Export"])

# ── GOVERNANCE: Trace analytics, rainbow ops ────────────────
from app.services.governance import trace_router
router.include_router(trace_router, tags=["Governance"])

# ── RAG MODULE: Knowledge retrieval, ingestion, evaluation ──
if settings.rag_enabled:
    from app.api.routes import knowledge, learning, evaluation, finetuning, pipelines

    router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
    router.include_router(learning.router, prefix="/learning", tags=["External Learning"])
    router.include_router(evaluation.router, prefix="/evaluation", tags=["RAG Evaluation"])
    router.include_router(finetuning.router, prefix="/finetuning", tags=["Fine-tuning SFT Data"])
    router.include_router(pipelines.router, prefix="/pipelines", tags=["Pipelines"])
    logger.info("📚 RAG module routes registered")
else:
    logger.info("📚 RAG module routes SKIPPED (mode={})", settings.PLATFORM_MODE.value)

# ── AGENT MODULE: Swarm orchestration, skills, MCP ──────────
if settings.agent_enabled:
    from app.api.routes import agents, generation

    router.include_router(agents.router, prefix="/agents", tags=["Agents"])
    router.include_router(generation.router, prefix="/generation", tags=["Generation"])
    logger.info("🤖 Agent module routes registered")
else:
    logger.info("🤖 Agent module routes SKIPPED (mode={})", settings.PLATFORM_MODE.value)
