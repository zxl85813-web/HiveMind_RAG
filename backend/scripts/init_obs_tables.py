import sys
import asyncio
from pathlib import Path

# 🏗️ [Path Fix]: Allow script to run independently
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.database import engine
from app.models.observability import SQLModel

async def init_tables():
    print("🚀 Initializing tables for observability...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("✅ Tables created.")

if __name__ == "__main__":
    asyncio.run(init_tables())
