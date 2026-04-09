
import asyncio
import sys
import os
from pathlib import Path

# Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

# Paths
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.vector_store import get_vector_store, VectorDocument
from app.core.embeddings import get_embedding_service
from loguru import logger

async def ingest_eval_data():
    logger.info("🚀 Starting Eval Data Ingestion...")
    
    store = get_vector_store()
    embedder = get_embedding_service()
    
    eval_files = [
        backend_dir / "data" / "eval" / "hr_policy.md",
        backend_dir / "data" / "eval" / "security_guide.py"
    ]
    
    for f_path in eval_files:
        if f_path.exists():
            content = f_path.read_text(encoding="utf-8")
            logger.info(f"📄 Embedding {f_path.name}...")
            # Use synchronous embed_query as defined in ZhipuEmbeddingService
            embedding = embedder.embed_query(content)
            doc = VectorDocument(page_content=content, metadata={"source": f_path.name}, embedding=embedding)
            await store.add_documents([doc], collection_name="eval_swarm")
            logger.info(f"✅ Ingested {f_path.name} into 'eval_swarm'")
        else:
            logger.warning(f"❌ File not found: {f_path}")

if __name__ == "__main__":
    import traceback
    try:
        asyncio.run(ingest_eval_data())
    except Exception:
        traceback.print_exc()
        sys.exit(1)

