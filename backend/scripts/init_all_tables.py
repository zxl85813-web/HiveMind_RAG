import sys
import asyncio
from pathlib import Path

# 🏗️ [Path Fix]: Allow script to run independently
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from sqlmodel import SQLModel
from app.core.database import engine

# Import ALL models to register them with SQLModel.metadata
from app.models.agents import *
from app.models.chat import *
from app.models.episodic import *
from app.models.evaluation import *
from app.models.finetuning import *
from app.models.intent import *
from app.models.knowledge import *
from app.models.observability import *
from app.models.pipeline_config import *
from app.models.security import *
from app.models.sync import *
from app.models.tags import *
from app.models.governance import *

async def init_all_tables():
    print("🚀 Initializing ALL database tables for governance and operations...")
    async with engine.begin() as conn:
        # This will create tables if they don't exist
        # Note: For SQLite, adding columns to existing tables might need Alembic, 
        # but in dev it often works if the DB is fresh or simple.
        await conn.run_sync(SQLModel.metadata.create_all)
    print("✅ All tables initialized.")

if __name__ == "__main__":
    asyncio.run(init_all_tables())
