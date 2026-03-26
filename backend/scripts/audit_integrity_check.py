"""
HiveMind Audit Integrity Checker v1.2 - CLEAN OUTPUT
"""
import os; import sys; import hashlib; from pathlib import Path; import asyncio; from sqlmodel import select
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")
from app.core.database import async_session_factory
from app.models.observability import RAGQueryTrace

async def verify_audit_chain():
    print("[AuditIntegrity] Verification started...")
    async with async_session_factory() as session:
        stmt = select(RAGQueryTrace).order_by(RAGQueryTrace.created_at)
        res = await session.execute(stmt); traces = res.scalars().all()
        if not traces: print("[AuditIntegrity] SUCCESS: No logs found (Clean start)."); return True
        errors = []; prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        for idx, t in enumerate(traces):
            if t.p_hash != prev_hash: errors.append(f"Broken Chain at Index {idx} (Trace: {t.id})")
            p = f"{t.p_hash}|{t.query}|{t.user_id}|{t.total_found}"
            calculated_hash = hashlib.sha256(p.encode()).hexdigest()
            if t.h_integrity != calculated_hash: errors.append(f"TAMPER DETECTED at Index {idx} (Trace: {t.id})")
            prev_hash = t.h_integrity
        if errors:
            print(f"[AuditIntegrity] FAILED: {len(errors)} ALERTS DETECTED.")
            for e in errors: print(f"  - {e}")
            return False
        else:
            print(f"[AuditIntegrity] SUCCESS: {len(traces)} logs intact and cryptographically linked.")
            return True

if __name__ == "__main__": asyncio.run(verify_audit_chain())
