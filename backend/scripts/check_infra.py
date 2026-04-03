import asyncio
import sys
from pathlib import Path

# 🏗️ [Path Fix]
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text
from redis import Redis
import httpx

async def check_db():
    print(f"📡 [DB] Connecting to: {settings.DATABASE_URL}...")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ [DB] Connected successfully.")
    except Exception as e:
        print(f"❌ [DB] Connection FAILED: {e}")

def check_redis():
    print(f"📡 [Redis] Connecting to: {settings.REDIS_URL}...")
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        print("✅ [Redis] Connected successfully.")
    except Exception as e:
        print(f"❌ [Redis] Connection FAILED: {e}")

async def check_embedding():
    print(f"📡 [Embedding] Checking {settings.EMBEDDING_PROVIDER} ({settings.EMBEDDING_MODEL})...")
    # Simple check for API Key presence
    if settings.EMBEDDING_API_KEY:
        print(f"✅ [Embedding] API Key present (Len: {len(settings.EMBEDDING_API_KEY)})")
    else:
        print("❌ [Embedding] API Key MISSING.")

async def main():
    print("\n" + "="*80)
    print("🛰️  HIVE-MIND INFRASTRUCTURE PULSE-CHECK")
    print("="*80)
    
    await check_db()
    check_redis()
    await check_embedding()
    
    print("\n🎯 [Summary]")
    print(f"    - Vector Store: {settings.VECTOR_STORE_TYPE}")
    print(f"    - DB Mode: {'PostgreSQL' if 'postgres' in settings.DATABASE_URL else 'SQLite'}")
    print(f"    - Graph DB: {settings.NEO4J_URI}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(main())
