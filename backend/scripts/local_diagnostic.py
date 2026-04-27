import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.sdk.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_db():
    print(f"[INFO] Checking Database Connection: {settings.DATABASE_URL}")
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"[SUCCESS] Database connection successful: {result.scalar()}")
        await engine.dispose()
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")

def check_dirs():
    print("[INFO] Checking Required Directories:")
    dirs = [settings.STORAGE_DIR, settings.UPLOAD_DIR, Path("logs")]
    for d in dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            test_file = d / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            print(f"[SUCCESS] Directory {d} is writable")
        except Exception as e:
            print(f"[ERROR] Directory {d} failed: {e}")

async def main():
    print("--- HiveMind Local Diagnostic Starting ---")
    print("-" * 40)
    print(f"Environment: {settings.ENV}")
    print(f"Debug: {settings.DEBUG}")
    print("-" * 40)
    
    check_dirs()
    await check_db()
    
    print("-" * 40)
    print("Diagnostic Complete")

if __name__ == "__main__":
    asyncio.run(main())
