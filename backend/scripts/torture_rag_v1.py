"""
HiveMind RAG Torture Test v3.6 — "The Core Truth (Final Fix)"

Final fix: No 'col_' prefix for collection names, matching ReadService.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except: pass

# Setup path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.core.database import async_session_factory
from app.models.chat import User
from app.models.knowledge import KnowledgeBase, Document
from app.models.security import DocumentPermission
from app.core.vector_store import VectorDocument
from app.services.retrieval.protocol import RetrievalContext
from app.services.retrieval.steps import AclFilterStep
from app.services.rag_gateway import RAGGateway

class VStore:
    def __init__(self): self.c = {}
    async def add_documents(self, docs, cn): self.c.setdefault(cn, []).extend(docs)
    async def search(self, query, k=4, collection_name=None, **kwargs):
        return self.c.get(collection_name, [])[:k]

async def mock_run(self, query, collection_names, top_k=150, user_id=None, **kwargs):
    from app.core.vector_store import get_vector_store
    ctx = RetrievalContext(query=query, kb_ids=collection_names, top_k=top_k, user_id=user_id)
    store = get_vector_store()
    for col in collection_names: ctx.candidates.extend(await store.search(query, k=top_k, collection_name=col))
    await AclFilterStep().execute(ctx)
    ctx.final_results = ctx.candidates[:top_k]
    return ctx.final_results, ctx.trace_log

async def mock_be(s, f, *a, **k):
    res = f(*a, **k); return await res if asyncio.iscoroutine(res) else res

class TortureTestRunner:
    def __init__(self):
        self.mv = VStore()
        from app.services.retrieval.pipeline import RetrievalPipeline
        self.p = [
            patch("app.core.vector_store.get_vector_store", return_value=self.mv),
            patch("app.core.graph_store.get_graph_store", return_value=MagicMock()),
            patch.object(RetrievalPipeline, "run", mock_run),
            patch("app.services.dependency_circuit_breaker.breaker_manager.execute", mock_be),
            patch("app.services.rag_gateway.RAGGateway._is_circuit_open", lambda s, k: False),
            patch("app.services.rag_gateway.RAGGateway._record_failure", lambda s, k: None),
        ]
        for it in self.p: it.start()
        self.gw = RAGGateway(); self.tid = int(time.time()); self.results = []
        self.kb = f"kb_{self.tid}"; self.ufin = f"f_{self.tid}"; self.uhr = f"h_{self.tid}"

    async def run(self):
        try:
            async with async_session_factory() as s:
                s.add(User(id=self.ufin, username=f"f{self.tid}", email=f"f{self.tid}@h.ai", department_id="finance", hashed_password="H", role="user"))
                s.add(User(id=self.uhr, username=f"h{self.tid}", email=f"h{self.tid}@h.ai", department_id="hr", hashed_password="H", role="user"))
                s.add(KnowledgeBase(id=self.kb, name="Audit KB", owner_id=self.ufin, vector_collection=self.kb))
                await s.commit()

            d1 = f"doc_f_{self.tid}"; d2 = f"doc_s_{self.tid}"
            async with async_session_factory() as s:
                s.add(Document(id=d1, filename="f.txt", file_type="txt", file_size=10, chunk_count=1, storage_path="/v", status="parsed"))
                s.add(DocumentPermission(document_id=d1, user_id=self.ufin, can_read=True))
                s.add(Document(id=d2, filename="s.txt", file_type="pdf", file_size=10, chunk_count=1, storage_path="/v", status="parsed"))
                s.add(DocumentPermission(document_id=d2, department_id="finance", can_read=True))
                await s.commit()

            # No 'col_' prefix, match 'kb_...'
            await self.mv.add_documents([VectorDocument(page_content="Fact Alice.", metadata={"document_id": d1})], self.kb)
            await self.mv.add_documents([VectorDocument(page_content="Secret budget.", metadata={"document_id": d2})], self.kb)

            # Audit Scenarios
            r1 = await self.gw.retrieve("Fact", [self.kb], user_id=self.ufin)
            r2_hr = await self.gw.retrieve("budget", [self.kb], user_id=self.uhr)
            r2_fin = await self.gw.retrieve("budget", [self.kb], user_id=self.ufin)
            
            p1 = len(r1.fragments) > 0
            p2 = (len(r2_hr.fragments) == 0) and (len(r2_fin.fragments) > 0)
            self.results = [{"s": "Fact Fidelity", "p": p1}, {"s": "ACL Isolation", "p": p2}]
        finally:
            for it in self.p: it.stop()
            log_dir = Path(backend_dir) / "logs" / "torture"; log_dir.mkdir(parents=True, exist_ok=True)
            report = f"# 🔨 RAG Torture Report (v3.6)\n\n"
            for r in self.results: report += f"| {r['s']} | {'✅ PASS' if r['p'] else '❌ FAIL'} |\n"
            with open(log_dir / "rag_torture_report.md", "w", encoding="utf-8") as f: f.write(report)
            print(f"\n[SUMMARY] {'ALL PASSED' if all(r['p'] for r in self.results) else 'SOME FAILED'}")

if __name__ == "__main__":
    from app.core.logging import setup_script_context
    setup_script_context("torture_v2")
    asyncio.run(TortureTestRunner().run())
