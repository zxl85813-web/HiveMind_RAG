"""
HiveMind RAG Torture Test v4.1 — "The Shadow Leak Audit" (Hardened)

Fixes:
- Ordered commits to satisfy Foreign Key constraints.
- Validated document and user persistence before permission assignment.
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
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.models.security import DocumentPermission
from app.core.vector_store import VectorDocument
from app.services.retrieval.protocol import RetrievalContext
from app.services.retrieval.steps import AclFilterStep, ParentChunkExpansionStep
from app.services.rag_gateway import RAGGateway

class VStore:
    def __init__(self): self.c = {}
    async def add_documents(self, docs, cn): self.c.setdefault(cn, []).extend(docs)
    async def search(self, q, k=4, collection_name=None, **kwargs):
        res = self.c.get(collection_name, [])
        return res[:k]

async def mock_run(self, query, collection_names, top_k=5, user_id=None, **kwargs):
    from app.core.vector_store import get_vector_store
    ctx = RetrievalContext(query=query, kb_ids=collection_names, top_k=top_k, user_id=user_id)
    store = get_vector_store()
    
    # Retrieval
    for col in collection_names: 
        ctx.candidates.extend(await store.search(query, k=top_k, collection_name=col))
    
    # 🚨 Step 1: ACL Filtering (Doc level)
    await AclFilterStep().execute(ctx)
    ctx.final_results = ctx.candidates[:top_k]
    
    # 🚨 Step 2: Parent Chunk Expansion (Vulnerability Point)
    await ParentChunkExpansionStep().execute(ctx)
    
    return ctx.final_results, ctx.trace_log

async def mock_be(s, f, *a, **k):
    res = f(*a, **k); return await res if asyncio.iscoroutine(res) else res

class ShadowLeakAuditRunner:
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
        self.kb = f"kb_{self.tid}"; self.u_fin = f"f_{self.tid}"

    async def setup_shadow_data(self):
        d_pub = f"doc_pub_{self.tid}"; d_priv = f"doc_priv_{self.tid}"
        cpriv_id = f"chunk_priv_{self.tid}"
        
        async with async_session_factory() as s:
            # 1. Create Finance User
            s.add(User(id=self.u_fin, username=f"f{self.tid}", email=f"f{self.tid}@h", department_id="finance", hashed_password="H", role="user"))
            # 2. Create Audit KB
            s.add(KnowledgeBase(id=self.kb, name="Audit KB", owner_id=self.u_fin, vector_collection=self.kb))
            # 3. Create Documents FIRST
            s.add(Document(id=d_pub, filename="public.txt", file_type="txt", file_size=10, chunk_count=1, storage_path="/v", status="parsed"))
            s.add(Document(id=d_priv, filename="private.txt", file_type="txt", file_size=10, chunk_count=1, storage_path="/v", status="parsed"))
            await s.commit()
            
        async with async_session_factory() as s:
            # 4. Create Permissions and Chunks SECOND (FK Safety)
            s.add(DocumentPermission(id=f"p1_{self.tid}", document_id=d_pub, department_id="finance", can_read=True))
            s.add(DocumentChunk(id=cpriv_id, document_id=d_priv, content="[CONFIDENTIAL] CEO Profit Share: 200%", chunk_index=0))
            await s.commit()
            
        # 5. Index Public Chunk pointing to Private Parent
        await self.mv.add_documents([
            VectorDocument(
                page_content="Company general document.", 
                metadata={
                    "document_id": d_pub, 
                    "parent_chunk_id": cpriv_id  # 💀 THE SHADOW LINK
                }
            )
        ], self.kb)

    async def run(self):
        try:
            await self.setup_shadow_data()
            print(f"DEBUG: Finance Auditor starting Audit...")
            res = await self.gw.retrieve("general", [self.kb], user_id=self.u_fin)
            
            # Validate: Did we leak Private Content?
            leaked = any("200%" in f.content for f in res.fragments)
            
            self.results = [{"s": "Cascading ACL Leak Audit", "p": not leaked, "d": "CRITICAL DATA LEAK DETECTED" if leaked else "Cascading ACL Secure"}]
        finally:
            for it in self.p: it.stop()
            log_dir = Path(backend_dir) / "logs" / "torture"; log_dir.mkdir(parents=True, exist_ok=True)
            report = f"# 🔒 RAG Security Audit Report (Cascading Leak)\n\n"
            for r in self.results: report += f"| Audit | Risk Status | Details |\n| :--- | :--- | :--- |\n| {r['s']} | {'✅ SECURE' if r['p'] else '🚨 CRITICAL LEAK'} | {r['d']} |\n"
            with open(log_dir / "rag_security_audit_report.md", "w", encoding="utf-8") as f: f.write(report)
            print(f"\n[SUMMARY] {'SECURITY AUDIT PASSED' if all(r['p'] for r in self.results) else '🚨 SECURITY BREACH DETECTED'}")

if __name__ == "__main__":
    from app.core.logging import setup_script_context
    setup_script_context("torture_security")
    asyncio.run(ShadowLeakAuditRunner().run())
