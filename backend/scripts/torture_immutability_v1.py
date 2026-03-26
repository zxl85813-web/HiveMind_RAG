"""
HiveMind Immutability Torture v1.3 - Using Production Recording logic
"""
import os; import sys; import time; from pathlib import Path; import asyncio; from sqlmodel import select
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")
from app.core.database import async_session_factory
from app.models.observability import RAGQueryTrace
from app.services.observability_service import record_rag_trace

async def run_immutability_challenge():
    print("[AuditTorture] Recording first legitimate trace through service...")
    await record_rag_trace(
        query="Legal Query", kb_ids=[], retrieval_strategy="hybrid",
        total_found=5, returned_count=5, latency_ms=10.0,
        retrieved_doc_ids=[], step_traces=[], user_id="user_valid"
    )
    
    # Get the ID of the trace we just made (the last one)
    async with async_session_factory() as s:
        res = await s.execute(select(RAGQueryTrace).order_by(RAGQueryTrace.created_at.desc()).limit(1))
        trace = res.scalar_one()
        trace_id = trace.id
    
    print(f"[AuditTorture] Targeting Trace: {trace_id} for attacks.")

    # STEP 2: Tamper Attempt (UPDATE)
    try:
        async with async_session_factory() as s:
            t = await s.get(RAGQueryTrace, trace_id)
            if t: t.user_id = "malicious_user"; s.add(t); await s.commit()
            t_s = "VULNERABLE"
    except Exception:
        t_s = "SECURE"

    # STEP 3: Wipe Attempt (DELETE)
    try:
        async with async_session_factory() as s:
            t = await s.get(RAGQueryTrace, trace_id)
            if t: await s.delete(t); await s.commit()
            w_s = "VULNERABLE"
    except Exception:
        w_s = "SECURE"

    print(f"[AuditTorture] Results - Tamper: {t_s}, Wipe: {w_s}")
    log_dir = Path(backend_dir) / "logs" / "torture"; log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "audit_immutability_report.md", "w", encoding="utf-8") as f:
        f.write(f"# Audit Immutability Report\n| Attack | Result |\n| :--- | :--- |\n| Tamper | {t_s} |\n| Wipe | {w_s} |")

if __name__ == "__main__": asyncio.run(run_immutability_challenge())
