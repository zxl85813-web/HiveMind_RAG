"""
HiveMind RAG Platform — FastAPI Application Entry Point
"""

from collections.abc import AsyncGenerator
import asyncio
from contextlib import asynccontextmanager

# @covers REQ-014
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

    # 1. Critical Initialization
    try:
        await init_db()  # Initialize Database
        await init_base_data()  # Seed critical data (Mock User etc.)
    except Exception as e:
        logger.critical(f"❌ Critical DB initialization failed: {e}")
        raise

    # 2. Agent Swarm Initialization
    from app.api.routes.agents import _swarm
    from app.agents.swarm import AgentDefinition
    
    logger.info("🐝 Registering Swarm Agents...")

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
            name="commerce_expert",
            description=(
                "电商业务专家。专门处理订单查询(01)、物流轨迹(02)、订单取消(03)和地址变更(04)。"
                "能够识别 EFXX, Amazon, eBay 等单号格式，并执行登录状态校验逻辑。"
            ),
            model_hint="balanced",
        )
    )
    _swarm.register_agent(
        AgentDefinition(
            name="email_expert",
            description=(
                "邮件客服专家。负责邮件分级 (L1-L5)、首回草稿生成和风控审核。"
                "擅长套用多语言模板，并能结合知识库和订单背景提供人性化回复。"
            ),
            model_hint="reasoning",
        )
    )
    _swarm.register_agent(
        AgentDefinition(
            name="critic",
            description="Audits agent responses for logic, safety, and hallucination risks.",
            icon="⚖️",
            model_hint="reasoning",
        )
    )
    _swarm.register_agent(AgentDefinition(name="Supervisor", description="Coordinator of the swarm", icon="👑"))

    logger.info(f"✅ Swarm initialized with {len(_swarm.get_agents())} agents.")

    # 3. Background Services (Delayed Start)
    _bg_tasks = []

    async def start_delayed_services():
        logger.info("⏳ Waiting 10s before starting background services...")
        await asyncio.sleep(10)
        
        try:
            from app.services.sync_service import sync_service
            await sync_service.start()
            logger.info("🚀 Background Sync Service started.")
        except Exception as e:
            logger.error(f"❌ Sync Service failed to start: {e}")

        try:
            from app.services.learning_service import LearningService
            async def run_learning_crawl_loop():
                interval = settings.LEARNING_FETCH_INTERVAL_HOURS * 3600
                while True:
                    try:
                        await LearningService.run_external_crawl()
                    except Exception as e:
                        logger.error(f"❌ Scheduled crawl failed: {e}")
                    await asyncio.sleep(interval)
            
            t = asyncio.create_task(run_learning_crawl_loop())
            _bg_tasks.append(t)
            logger.info("🚀 Learning Crawl Task scheduled.")
        except Exception as e:
            logger.error(f"❌ Learning Service failed to schedule: {e}")

    startup_task = asyncio.create_task(start_delayed_services())
    _bg_tasks.append(startup_task)
    logger.info("✅ Lifespan startup completed (Background tasks deferred).")
    
    yield

    logger.info("🐝 HiveMind RAG Platform shutting down...")
    for t in _bg_tasks:
        if not t.done():
            t.cancel()
    
    try:
        from app.services.sync_service import sync_service
        await sync_service.stop()
    except Exception:
        pass
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
