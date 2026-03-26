"""
HiveMind Audit Migration (v1.1)

Fixed: 
- Ensured ENV loading from absolute path 'backend/.env'.
- Sanitized prints (no emojis).
- Logs DATABASE_URL type for debugging.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))

# Force load .env from the correct directory BEFORE config initialized
env_path = backend_dir / ".env"
load_dotenv(env_path)

# Verify if env loaded
if "POSTGRES_PASSWORD" not in os.environ:
    print(f"WARNING: POSTGRES_PASSWORD not in os.environ! Tried: {env_path}")

from app.core.config import settings
from app.core.database import async_session_factory
from sqlalchemy import text
import asyncio

async def migrate_audit():
    print(f"[AuditMigration] Database Type: {'SQLite' if 'sqlite' in settings.DATABASE_URL else 'PostgreSQL'}")
    print("[AuditMigration] Adding integrity columns to obs_rag_query_traces...")
    
    commands = [
        "ALTER TABLE obs_rag_query_traces ADD COLUMN IF NOT EXISTS p_hash VARCHAR;",
        "ALTER TABLE obs_rag_query_traces ADD COLUMN IF NOT EXISTS h_integrity VARCHAR;",
        "CREATE INDEX IF NOT EXISTS idx_obs_rag_p_hash ON obs_rag_query_traces (p_hash);",
        "CREATE INDEX IF NOT EXISTS idx_obs_rag_h_integrity ON obs_rag_query_traces (h_integrity);"
    ]
    
    try:
        async with async_session_factory() as s:
            for cmd in commands:
                await s.execute(text(cmd))
            await s.commit()
            print("[AuditMigration] SUCCESS: Columns added.")
    except Exception as e:
        print(f"[AuditMigration] FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_audit())
