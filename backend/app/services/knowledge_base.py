"""
Knowledge Base Service — Manages KB and Document persistence.

所属模块: services
依赖模块: models.knowledge, core.database
注册位置: REGISTRY.md > Services > KnowledgeService
"""
from typing import Sequence
from sqlmodel import Session, select
from app.models.knowledge import KnowledgeBase, Document, KnowledgeBaseDocumentLink
from app.core.exceptions import NotFoundError

class KnowledgeService:
    def __init__(self, session: Session):
        self.session = session

    def create_kb(self, kb: KnowledgeBase) -> KnowledgeBase:
        self.session.add(kb)
        self.session.commit()
        self.session.refresh(kb)
        return kb

    def get_kb(self, kb_id: str) -> KnowledgeBase:
        kb = self.session.get(KnowledgeBase, kb_id)
        if not kb:
            raise NotFoundError(resource="knowledge_base", id=kb_id)
        return kb

    def list_kbs(self, owner_id: str) -> Sequence[KnowledgeBase]:
        statement = select(KnowledgeBase).where(KnowledgeBase.owner_id == owner_id)
        return self.session.exec(statement).all()

    def create_document(self, doc: Document) -> Document:
        """Create a new global document entry."""
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)
        return doc
        
    def get_document(self, doc_id: str) -> Document:
        doc = self.session.get(Document, doc_id)
        if not doc:
            raise NotFoundError(resource="document", id=doc_id)
        return doc

    def link_document_to_kb(self, kb_id: str, doc_id: str) -> KnowledgeBaseDocumentLink:
        """Link a document to a Knowledge Base and increment KB version."""
        # Validate existence
        self.get_kb(kb_id)
        self.get_document(doc_id)

        # Check if already linked
        link = self.session.get(KnowledgeBaseDocumentLink, (kb_id, doc_id))
        if link:
            return link
            
        link = KnowledgeBaseDocumentLink(knowledge_base_id=kb_id, document_id=doc_id)
        self.session.add(link)
        
        # Increment version
        # We need to fetch KB again or reuse. get_kb returned valid object but not attached to session variable here?
        # self.get_kb returns object bound to session.
        kb = self.session.get(KnowledgeBase, kb_id)
        if kb:
            kb.version += 1
            self.session.add(kb)
        
        self.session.commit()
        self.session.refresh(link)
        return link

    def list_documents_in_kb(self, kb_id: str) -> Sequence[Document]:
        """List all documents linked to a specific KB."""
        statement = (
            select(Document)
            .join(KnowledgeBaseDocumentLink)
            .where(KnowledgeBaseDocumentLink.knowledge_base_id == kb_id)
        )
        return self.session.exec(statement).all()

    def unlink_document(self, kb_id: str, doc_id: str):
        """Unlink a document from a KB."""
        link = self.session.get(KnowledgeBaseDocumentLink, (kb_id, doc_id))
        if link:
            self.session.delete(link)
            kb = self.session.get(KnowledgeBase, kb_id)
            if kb:
                kb.version += 1
                self.session.add(kb)
            self.session.commit()
