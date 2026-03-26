"""
HiveMind Audit Hardening (v1.1) - Hard Immutability via SQL Trigger
"""
import os
import sys
from pathlib import Path
from sqlalchemy import text
import asyncio

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.core.database import async_session_factory

async def apply_hard_immutability():
    print("[AuditHardening] Deploying SQL Immutability Trigger...")
    sql_func = "CREATE OR REPLACE FUNCTION block_audit_mod() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION 'AUDIT_LOCKED'; END; $$ LANGUAGE plpgsql;"
    sql_trig = "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'ai_trig') THEN CREATE TRIGGER ai_trig BEFORE UPDATE OR DELETE ON obs_rag_query_traces FOR EACH ROW EXECUTE FUNCTION block_audit_mod(); END IF; END; $$;"
    async with async_session_factory() as s:
        await s.execute(text(sql_func)); await s.execute(text(sql_trig)); await s.commit()
        print("[AuditHardening] SUCCESS: Trigger Armed.")

if __name__ == "__main__": asyncio.run(apply_hard_immutability())
