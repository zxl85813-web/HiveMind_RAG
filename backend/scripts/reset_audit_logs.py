"""
HiveMind Audit Reset Script
"""
import asyncio; from sqlalchemy import text; from pathlib import Path; import os; import sys
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")
from app.core.database import async_session_factory

async def reset():
    print("[AuditReset] Clearing logs and dropping triggers for a fresh start...")
    async with async_session_factory() as s:
        await s.execute(text("DROP TRIGGER IF EXISTS ai_trig ON obs_rag_query_traces;"))
        await s.execute(text("DELETE FROM obs_rag_query_traces;"))
        await s.commit()
    print("[AuditReset] Done.")

if __name__ == "__main__": asyncio.run(reset())
