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

    # TODO: Initialize Redis, Vector Store, MCP connections
    # TODO: Initialize Agent Swarm
    # TODO: Initialize WebSocket manager

    yield

    logger.info("🐝 HiveMind RAG Platform shutting down...")
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
