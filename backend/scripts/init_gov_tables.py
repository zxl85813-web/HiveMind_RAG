import sys
import asyncio
from pathlib import Path

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("init_gov_tables")
t_logger = get_trace_logger("scripts.governance")

from sqlmodel import SQLModel
from app.core.database import engine
from app.models.governance import PromptDefinition

async def init_tables():
    t_logger.info("🚀 Initializing tables for Prompt Governance...", action="db_init_start")
    async with engine.begin() as conn:
        # Create all tables associated with SQLModel.metadata
        await conn.run_sync(SQLModel.metadata.create_all)
    t_logger.success("✅ Governance tables created.", action="db_init_success")

if __name__ == "__main__":
    asyncio.run(init_tables())
