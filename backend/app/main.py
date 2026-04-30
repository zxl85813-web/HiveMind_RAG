"""
HiveMind RAG Platform — FastAPI Application Entry Point

Supports three deployment modes via PLATFORM_MODE env var:
  - "full"  : RAG + Agent (default)
  - "rag"   : Knowledge retrieval platform only
  - "agent" : Agent orchestration platform only
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import router as api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager — conditionally initializes modules."""
    mode = settings.PLATFORM_MODE.value
    logger.info("🐝 HiveMind starting up in [{}] mode...", mode)

    # ── CORE: Always initialize ─────────────────────────────
    from app.core.database import close_db, init_db
    from app.core.init_data import init_base_data

    await init_db()
    await init_base_data()

    # ── AGENT MODULE: Swarm + Skills + MCP ──────────────────
    if settings.agent_enabled:
        from app.api.routes.agents import _swarm
        from app.agents.swarm import AgentDefinition

        # Register default agents
        _swarm.register_agent(AgentDefinition(
            name="web",
            description="Able to search the internet for the most up-to-date information.",
            model_hint="fast",
        ))
        _swarm.register_agent(AgentDefinition(
            name="code",
            description="Specialized in writing, debugging, and explaining code in various programming languages.",
            model_hint="reasoning",
        ))

        # RAG agent only makes sense when RAG is also enabled
        if settings.rag_enabled:
            _swarm.register_agent(AgentDefinition(
                name="rag",
                description="Knowledge Expert. Use this for ANY factual questions, knowledge base lookups, or internal documentation queries.",
                model_hint="balanced",
            ))
            _swarm.register_agent(AgentDefinition(
                name="eval_architect",
                description="Expert in RAG evaluation systems. Helps users design testsets, expand data with AI, and diagnose quality issues.",
                model_hint="reasoning",
            ))

        agent_names = [a.name for a in _swarm._agents.values()] if hasattr(_swarm, '_agents') else []
        logger.info("🤖 Agent Swarm initialized with agents: {}", agent_names)
    else:
        logger.info("🤖 Agent Swarm SKIPPED (mode={})", mode)

    # ── RAG MODULE: Sync service, indexing background tasks ──
    sync_svc = None
    if settings.rag_enabled:
        from app.services.sync_service import sync_service
        sync_svc = sync_service
        await sync_svc.start()
        logger.info("📚 RAG background services started")
    else:
        logger.info("📚 RAG background services SKIPPED (mode={})", mode)

    # ── Token accountant flusher (multi-tenant cost tracking) ───
    try:
        from app.services.governance.token_accountant import start_background_flusher
        start_background_flusher()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Token accountant flusher not started: {}", exc)

    logger.info("🐝 HiveMind ready — mode={}, rag={}, agent={}", mode, settings.rag_enabled, settings.agent_enabled)

    yield

    # ── Shutdown ────────────────────────────────────────────
    logger.info("🐝 HiveMind shutting down...")
    try:
        from app.services.governance.token_accountant import stop_background_flusher, get_token_accountant
        from app.core.database import get_db_session
        # Final flush so we don't lose the last 30s of usage data on shutdown
        async for session in get_db_session():
            await get_token_accountant().flush(session)
            break
        await stop_background_flusher()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Token accountant shutdown skipped: {}", exc)
    if sync_svc:
        await sync_svc.stop()
    await close_db()


# ── App title reflects the active mode ──────────────────────
_MODE_TITLES = {
    "rag": "HiveMind RAG Platform",
    "agent": "HiveMind Agent Platform",
    "full": "HiveMind RAG + Agent Platform",
}

app = FastAPI(
    title=_MODE_TITLES.get(settings.PLATFORM_MODE.value, settings.APP_NAME),
    version=settings.APP_VERSION,
    description=f"Enterprise AI platform — running in [{settings.PLATFORM_MODE.value}] mode",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes (already filtered by PLATFORM_MODE in app.api.__init__)
app.include_router(api_router, prefix="/api/v1")
