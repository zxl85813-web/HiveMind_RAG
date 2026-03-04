"""
Knowledge Base Service — Manages KB and Document persistence.

所属模块: services
依赖模块: models.knowledge, core.database
注册位置: REGISTRY.md > Services > KnowledgeService
"""
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.knowledge import KnowledgeBase, Document, KnowledgeBaseDocumentLink
from app.core.exceptions import NotFoundError

class KnowledgeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_kb(self, kb: KnowledgeBase) -> KnowledgeBase:
        self.session.add(kb)
        await self.session.commit()
        await self.session.refresh(kb)
        return kb

    async def get_kb(self, kb_id: str) -> KnowledgeBase:
        kb = await self.session.get(KnowledgeBase, kb_id)
        if not kb:
            raise NotFoundError(resource="knowledge_base", id=kb_id)
        return kb

    async def list_kbs(self, owner_id: str) -> Sequence[KnowledgeBase]:
        statement = select(KnowledgeBase).where(KnowledgeBase.owner_id == owner_id)
        res = await self.session.execute(statement)
        return res.scalars().all()

    async def create_document(self, doc: Document) -> Document:
        """Create a new global document entry."""
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc
        
    async def get_document(self, doc_id: str) -> Document:
        doc = await self.session.get(Document, doc_id)
        if not doc:
            raise NotFoundError(resource="document", id=doc_id)
        return doc

    async def link_document_to_kb(self, kb_id: str, doc_id: str) -> KnowledgeBaseDocumentLink:
        """Link a document to a Knowledge Base and increment KB version."""
        # Validate existence
        await self.get_kb(kb_id)
        await self.get_document(doc_id)

        # Check if already linked
        link = await self.session.get(KnowledgeBaseDocumentLink, (kb_id, doc_id))
        if link:
            return link
            
        link = KnowledgeBaseDocumentLink(knowledge_base_id=kb_id, document_id=doc_id)
        self.session.add(link)
        
        # Increment version
        kb = await self.session.get(KnowledgeBase, kb_id)
        if kb:
            kb.version += 1
            self.session.add(kb)
        
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def list_documents_in_kb(self, kb_id: str) -> Sequence[Document]:
        """List all documents linked to a specific KB."""
        from sqlalchemy.orm import selectinload
        statement = (
            select(Document)
            .join(KnowledgeBaseDocumentLink)
            .where(KnowledgeBaseDocumentLink.knowledge_base_id == kb_id)
            .options(selectinload(Document.tags))
        )
        res = await self.session.execute(statement)
        return res.scalars().unique().all()

    async def unlink_document(self, kb_id: str, doc_id: str):
        """Unlink a document from a KB."""
        link = await self.session.get(KnowledgeBaseDocumentLink, (kb_id, doc_id))
        if link:
            await self.session.delete(link)
            kb = await self.session.get(KnowledgeBase, kb_id)
            if kb:
                kb.version += 1
                self.session.add(kb)
            await self.session.commit()
