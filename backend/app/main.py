"""
HiveMind RAG Platform — FastAPI Application Entry Point
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
            description="Knowledge Expert. Use this for ANY factual questions, knowledge base lookups, or internal documentation queries. It excels at extracting precise answers with citations.",
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
            description="Expert in RAG evaluation systems. Helps users design testsets, expand data with AI, and diagnose quality issues.",
            model_hint="reasoning",
        )
    )

    logger.info("🐝 Agent Swarm initialized with 3 agents (rag, web, code)")

    # Start External Source Background Sync Service
    from app.services.sync_service import sync_service

    await sync_service.start()

    # TODO: Initialize WebSocket manager

    yield

    logger.info("🐝 HiveMind RAG Platform shutting down...")
    await sync_service.stop()
    await close_db()
    # TODO: Cleanup resources


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise RAG platform with Agent Swarm architecture",
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

# Mount API routes
app.include_router(api_router, prefix="/api/v1")
