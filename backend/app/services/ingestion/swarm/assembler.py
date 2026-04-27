"""
Swarm Assembler Service (V3 Architecture).

Restores the functional chunking and vectorization logic that was previously
housed in the linear IngestionExecutor stages.

Graph Alignment (对齐文档与图谱):
  - Gap 1 fixed: folder_path 写入图谱，保留目录结构
  - Gap 2 fixed: 创建 KnowledgeBase 节点 + BELONGS_TO 关系
  - Gap 3 fixed: 调用 extract_and_store() 提取语义实体
  - Gap 4 fixed: 创建 Chunk 节点 + CONTAINS_CHUNK 关系
"""

from typing import Any

from loguru import logger

from app.batch.ingestion.chunking import ChunkingStrategyRegistry
from app.core.database import async_session_factory
from app.core.embeddings import get_embedding_service
from app.core.vector_store import VectorDocument, get_vector_store
from app.models.knowledge import KnowledgeBase


class SwarmAssembler:
    """
    Handles the 'Honey-Making' phase: turning raw text into searchable knowledge.
    """

    @staticmethod
    async def process_and_vectorize(
        kb_id: str,
        doc_id: str,
        raw_text: str,
        sections: list[dict[str, Any]],
        chunking_strategy: str = "recursive",
        code_structure: dict[str, Any] | None = None,
        enrichment_data: dict[str, Any] | None = None,
        folder_path: str | None = None,          # Gap-1: 文件夹路径
        filename: str | None = None,             # 可选：文件名，用于图谱节点展示
    ) -> dict[str, Any]:
        """
        Consolidated logic for chunking, vectorization, and graph alignment.
        """
        logger.info(f"🧩 [Assembler] Processing Doc {doc_id} for KB {kb_id}")

        # 1. Chunking
        strategy = ChunkingStrategyRegistry.get_strategy(chunking_strategy)
        from app.batch.ingestion.protocol import DocumentSection, ResourceMetadata, ResourceType, StandardizedResource

        resource = StandardizedResource(
            meta=ResourceMetadata(filename=doc_id, file_path=doc_id, resource_type=ResourceType.OTHER),
            raw_text=raw_text,
            sections=[DocumentSection(**s) for s in sections],
            tables=[],
            images=[],
        )

        chunks = strategy.chunk(doc_id=doc_id, resource=resource)

        # 2. Persist Chunks to SQL
        async with async_session_factory() as session:
            for c in chunks:
                session.add(c)
            await session.commit()

        # 3. Vectorization
        try:
            async with async_session_factory() as session:
                kb = await session.get(KnowledgeBase, kb_id)
                if not kb:
                    raise Exception(f"KB {kb_id} not found")
                collection_name = kb.vector_collection
                kb_name = kb.name

            embedder = get_embedding_service()
            vector_docs = []

            for c in chunks:
                meta = {
                    "chunk_id": c.id,
                    "kb_id": kb_id,
                    "doc_id": doc_id,
                    "chunk_index": c.chunk_index,
                    "folder_path": folder_path or "",
                }
                vector_docs.append(VectorDocument(page_content=c.content, metadata=meta))

            if vector_docs:
                texts = [d.page_content for d in vector_docs]
                embeddings = embedder.embed_documents(texts)
                for i, d in enumerate(vector_docs):
                    d.embedding = embeddings[i]

                store = get_vector_store()
                await store.add_documents(vector_docs, collection_name=collection_name)

            # ── 图谱对齐 ─────────────────────────────────────────────────────
            from app.services.memory.tier.graph_index import graph_index

            # Gap-2: 确保 KnowledgeBase 节点存在，并建立 Document BELONGS_TO KB 关系
            await SwarmAssembler._sync_kb_document_graph(
                graph_index=graph_index,
                kb_id=kb_id,
                kb_name=kb_name,
                doc_id=doc_id,
                filename=filename or doc_id,
                folder_path=folder_path,
            )

            # Gap-4: 将 Chunk 节点写入图谱，建立 CONTAINS_CHUNK 关系
            if chunks:
                await SwarmAssembler._sync_chunks_graph(
                    graph_index=graph_index,
                    doc_id=doc_id,
                    chunks=chunks,
                )

            # Gap-3: 语义实体提取（从原始文本中提取实体三元组）
            if raw_text and len(raw_text) > 100:
                await graph_index.extract_and_store(doc_id, raw_text[:8000])

            # Gap-1 + 原有: Code Vault Indexing (M7.2)
            if code_structure:
                await graph_index.index_code_structure(doc_id, code_structure)

            # Gap-1 + 原有: Enrichment Indexing (P1-1)，补充 folder_path
            if enrichment_data:
                enrichment_with_folder = {
                    **enrichment_data,
                    "folder_path": folder_path,   # Gap-1: 注入文件夹路径
                }
                await graph_index.index_enrichment_data(doc_id, enrichment_with_folder, kb_id=kb_id)

            logger.success(
                f"✅ [Assembler] Doc {doc_id}: {len(vector_docs)} chunks vectorized, "
                f"graph aligned (kb_rel={True}, chunks={len(chunks)}, "
                f"folder={folder_path or 'root'})"
            )
            return {
                "chunks_created": len(chunks),
                "status": "vectorized",
                "has_code_structure": code_structure is not None,
                "has_enrichment": enrichment_data is not None,
                "graph_aligned": True,
            }

        except Exception as e:
            logger.error(f"❌ [Assembler] Vectorization failed: {e}")
            raise e

    # ── 图谱对齐辅助方法 ──────────────────────────────────────────────────────

    @staticmethod
    async def _sync_kb_document_graph(
        graph_index,
        kb_id: str,
        kb_name: str,
        doc_id: str,
        filename: str,
        folder_path: str | None,
    ) -> None:
        """
        Gap-2: 确保图谱中存在 KnowledgeBase 节点，并建立：
          (:KnowledgeBase)-[:CONTAINS_DOCUMENT]->(:Document)
          (:Document)-[:IN_FOLDER]->(:Folder)  （当 folder_path 存在时）
        """
        if not graph_index._is_available():
            return

        import time
        ts = int(time.time() * 1000)

        # 1. MERGE KnowledgeBase 节点
        kb_cypher = """
        MERGE (kb:ArchNode:KnowledgeBase {id: $kb_id})
        SET kb.name = $kb_name,
            kb.type = 'KnowledgeBase',
            kb.updated_at = $ts
        """
        await graph_index.store.execute_query(kb_cypher, {
            "kb_id": kb_id, "kb_name": kb_name, "ts": ts
        })

        # 2. MERGE Document 节点（补充 folder_path 和 filename）
        doc_cypher = """
        MERGE (d:ArchNode:Document {id: $doc_id})
        SET d.name     = $filename,
            d.filename = $filename,
            d.kb_id    = $kb_id,
            d.folder_path = $folder_path,
            d.path     = $doc_id,
            d.type     = 'Document',
            d.updated_at = $ts
        WITH d
        MATCH (kb:KnowledgeBase {id: $kb_id})
        MERGE (kb)-[:CONTAINS_DOCUMENT]->(d)
        """
        await graph_index.store.execute_query(doc_cypher, {
            "doc_id": doc_id,
            "filename": filename,
            "kb_id": kb_id,
            "folder_path": folder_path or "",
            "ts": ts,
        })

        # 3. 如果有 folder_path，建立文件夹层级节点
        if folder_path:
            parts = folder_path.strip("/").split("/")
            parent_id = f"FOLDER:{kb_id}:root"

            # 确保 root 节点存在
            await graph_index.store.execute_query(
                "MERGE (f:ArchNode:Folder {id: $id}) SET f.name = 'root', f.type = 'Folder', f.kb_id = $kb_id",
                {"id": parent_id, "kb_id": kb_id}
            )

            # 逐级建立文件夹节点和 PARENT_FOLDER 关系
            for part in parts:
                folder_id = f"FOLDER:{kb_id}:{folder_path[:folder_path.index(part) + len(part)]}"
                folder_cypher = """
                MERGE (f:ArchNode:Folder {id: $folder_id})
                SET f.name = $name, f.type = 'Folder', f.kb_id = $kb_id
                WITH f
                MATCH (parent:Folder {id: $parent_id})
                MERGE (parent)-[:CONTAINS_FOLDER]->(f)
                """
                await graph_index.store.execute_query(folder_cypher, {
                    "folder_id": folder_id,
                    "name": part,
                    "kb_id": kb_id,
                    "parent_id": parent_id,
                })
                parent_id = folder_id

            # 文档挂到最深层文件夹
            await graph_index.store.execute_query(
                """
                MATCH (f:Folder {id: $folder_id}), (d:Document {id: $doc_id})
                MERGE (f)-[:CONTAINS_DOCUMENT]->(d)
                """,
                {"folder_id": parent_id, "doc_id": doc_id}
            )

    @staticmethod
    async def _sync_chunks_graph(graph_index, doc_id: str, chunks: list) -> None:
        """
        Gap-4: 将 DocumentChunk 写入图谱，建立：
          (:Document)-[:CONTAINS_CHUNK]->(:Chunk)
          (:Chunk)-[:NEXT_CHUNK]->(:Chunk)  （顺序链）
        """
        if not graph_index._is_available() or not chunks:
            return

        import time
        ts = int(time.time() * 1000)

        # 批量 MERGE Chunk 节点
        chunk_nodes = [
            {
                "id": f"CHUNK:{c.id}",
                "chunk_db_id": c.id,
                "doc_id": doc_id,
                "chunk_index": c.chunk_index,
                "content_preview": c.content[:200] if c.content else "",
                "ts": ts,
            }
            for c in chunks
        ]

        batch_cypher = """
        UNWIND $chunks AS c
        MERGE (ch:ArchNode:Chunk {id: c.id})
        SET ch.chunk_db_id  = c.chunk_db_id,
            ch.doc_id       = c.doc_id,
            ch.chunk_index  = c.chunk_index,
            ch.preview      = c.content_preview,
            ch.type         = 'Chunk',
            ch.updated_at   = c.ts
        WITH ch, c
        MATCH (d:Document {id: c.doc_id})
        MERGE (d)-[:CONTAINS_CHUNK]->(ch)
        """
        await graph_index.store.execute_query(batch_cypher, {"chunks": chunk_nodes})

        # 建立顺序链 NEXT_CHUNK（按 chunk_index 排序）
        sorted_chunks = sorted(chunks, key=lambda x: x.chunk_index)
        for i in range(len(sorted_chunks) - 1):
            await graph_index.store.execute_query(
                """
                MATCH (a:Chunk {id: $a_id}), (b:Chunk {id: $b_id})
                MERGE (a)-[:NEXT_CHUNK]->(b)
                """,
                {
                    "a_id": f"CHUNK:{sorted_chunks[i].id}",
                    "b_id": f"CHUNK:{sorted_chunks[i + 1].id}",
                }
            )
