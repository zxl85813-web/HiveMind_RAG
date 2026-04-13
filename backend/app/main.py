"""
HiveMind RAG Platform — FastAPI Application Entry Point
"""

from collections.abc import AsyncGenerator
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import router as api_router
from app.core.config import settings
from app.sdk.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager."""
    logger.info("🐝 HiveMind RAG Platform starting up...")

    # Initialize Core Services
    from app.core.database import close_db, init_db
    from app.core.init_data import init_base_data

    await init_db()  # Initialize Database (Auto-migration in dev)
    await init_base_data()  # Seed critical data (Mock User etc.)

    # Initialize Agent Swarm
    from app.agents.swarm import AgentDefinition
    from app.api.routes.agents import _swarm

    # Registering default agents (MVP)
    _swarm.register_agent(
        AgentDefinition(
            name="rag",
            description=(
                "Knowledge Expert. Use this for factual questions, knowledge-base lookups, "
                "or internal documentation queries with citations."
            ),
            model_hint="balanced",
        )
    )
    _swarm.register_agent(
        AgentDefinition(
            name="web",
            description="Able to search the internet for the most up-to-date information.",
            model_hint="fast",
        )
    )
    _swarm.register_agent(
        AgentDefinition(
            name="code",
            description="Specialized in writing, debugging, and explaining code in various programming languages.",
            model_hint="reasoning",
        )
    )
    _swarm.register_agent(
        AgentDefinition(
            name="eval_architect",
            description=(
                "Expert in RAG evaluation systems. Helps design testsets, expand data with AI, "
                "and diagnose quality issues."
            ),
            model_hint="reasoning",
        )
    )
    _swarm.register_agent(
        AgentDefinition(
            name="critic",
            description="Quality control and compliance agent. Reviews generated content for safety and accuracy.",
            model_hint="reasoning",
        )
    )

    logger.info("🐝 Agent Swarm initialized with 5 agents (rag, web, code, eval_architect, critic)")

    # Start External Source Background Sync Service
    from app.services.sync_service import sync_service

    await sync_service.start()

    # 🌐 [Native Scheduler]: Replacement for APScheduler
    async def run_learning_crawl_loop():
        from app.services.learning_service import LearningService
        from app.core.config import settings as _cfg
        
        interval = _cfg.LEARNING_FETCH_INTERVAL_HOURS * 3600
        logger.info("🌐 Native Learning Crawler loop started (Interval: {} hours).", _cfg.LEARNING_FETCH_INTERVAL_HOURS)
        
        while True:
            try:
                await LearningService.run_external_crawl()
            except Exception as e:
                logger.error("❌ Scheduled crawl failed: {}", e)
            
            await asyncio.sleep(interval)

    # Start External Source Background Sync Service
    from app.services.sync_service import sync_service
    await sync_service.start()

    # Start native crawler task
    crawler_task = asyncio.create_task(run_learning_crawl_loop())

    # TODO: Initialize WebSocket manager

    yield

    logger.info("🐝 HiveMind RAG Platform shutting down...")
    crawler_task.cancel()
    await sync_service.stop()
    await close_db()
    # TODO: Cleanup resources


import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import trace_id_var

class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 🛰️ [Context Restoration]: Fetch from Headers or generate
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        # 🔄 [Sequence Hardening]: Echo client's sequence or generate timestamp-based one
        request_seq = request.headers.get("X-Request-Sequence") or str(int(time.time() * 1000))
        
        token = trace_id_var.set(trace_id)
        try:
            response = await call_next(request)
            
            # 🛡️ [API Unification Headers]
            response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Response-Sequence"] = request_seq
            response.headers["X-Response-Timestamp"] = str(int(time.time() * 1000))
            
            return response
        finally:
            trace_id_var.reset(token)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise RAG platform with Agent Swarm architecture",
    lifespan=lifespan,
)

app.add_middleware(TraceMiddleware)
register_exception_handlers(app)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api/v1")
