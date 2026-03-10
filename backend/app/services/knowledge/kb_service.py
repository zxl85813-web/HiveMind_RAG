"""
Knowledge Base Service — Manages KB and Document persistence.

所属模块: services/knowledge
依赖模块: models.knowledge, core.database
注册位置: REGISTRY.md > Services > KnowledgeService
"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import or_, select

from app.core.exceptions import NotFoundError
from app.models.chat import User
from app.models.knowledge import Document, KnowledgeBase, KnowledgeBaseDocumentLink
from app.models.security import KnowledgeBasePermission


class KnowledgeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_kb(self, kb: KnowledgeBase) -> KnowledgeBase:
        self.session.add(kb)
        await self.session.commit()
        await self.session.refresh(kb)

        # Add Owner ACL rule
        kb_perm = KnowledgeBasePermission(
            kb_id=kb.id, user_id=kb.owner_id, can_read=True, can_write=True, can_manage=True
        )
        self.session.add(kb_perm)
        await self.session.commit()

        return kb

    async def get_kb(self, kb_id: str) -> KnowledgeBase:
        kb = await self.session.get(KnowledgeBase, kb_id)
        if not kb:
            raise NotFoundError(resource="knowledge_base", resource_id=kb_id)
        return kb

    async def list_kbs(self, current_user: User) -> Sequence[KnowledgeBase]:
        """List all knowledge bases that the user has read access to."""
        if current_user.role == "admin":
            statement = select(KnowledgeBase)
        else:
            # Accessible if user is owner, or public, or has read permission based on user/role/department
            conditions = [KnowledgeBase.owner_id == current_user.id, KnowledgeBase.is_public]

            # ACL Subquery
            acl_stmt = select(KnowledgeBasePermission.kb_id).where(
                KnowledgeBasePermission.can_read,
                or_(
                    KnowledgeBasePermission.user_id == current_user.id,
                    KnowledgeBasePermission.role_id == current_user.role,
                    (
                        KnowledgeBasePermission.department_id == current_user.department_id
                        if current_user.department_id
                        else False
                    ),
                ),
            )
            conditions.append(KnowledgeBase.id.in_(acl_stmt))

            statement = select(KnowledgeBase).where(or_(*conditions))

        res = await self.session.execute(statement)
        return res.scalars().all()

    async def get_user_accessible_kbs(self, current_user: User) -> list[str]:
        """Return a list of KB IDs that the user can read."""
        kbs = await self.list_kbs(current_user)
        return [kb.id for kb in kbs]

    async def check_kb_access(self, kb_id: str, user: User, level: str = "read") -> bool:
        """Check if user has specific access level to KB."""
        if user.role == "admin":
            return True

        kb = await self.session.get(KnowledgeBase, kb_id)
        if not kb:
            return False

        if kb.is_public and level == "read":
            return True

        if kb.owner_id == user.id:
            return True

        # Check ACL
        acl_stmt = select(KnowledgeBasePermission).where(
            KnowledgeBasePermission.kb_id == kb_id,
            or_(
                KnowledgeBasePermission.user_id == user.id,
                KnowledgeBasePermission.role_id == user.role,
                KnowledgeBasePermission.department_id == user.department_id if user.department_id else False,
            ),
        )
        res = await self.session.execute(acl_stmt)
        perms = res.scalars().all()

        for p in perms:
            if level == "read" and p.can_read:
                return True
            if level == "write" and p.can_write:
                return True
            if level == "manage" and p.can_manage:
                return True

        return False

    async def create_document(self, doc: Document) -> Document:
        """Create a new global document entry."""
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def get_document(self, doc_id: str) -> Document:
        doc = await self.session.get(Document, doc_id)
        if not doc:
            raise NotFoundError(resource="document", resource_id=doc_id)
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
