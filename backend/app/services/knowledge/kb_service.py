"""
Knowledge Base Service — Manages KB and Document persistence.

所属模块: services/knowledge
依赖模块: models.knowledge, core.database
注册位置: REGISTRY.md > Services > KnowledgeService
"""

import json
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import or_, select

from app.core.exceptions import NotFoundError
from app.core.logging import logger
from app.models.chat import User
from app.models.knowledge import Document, KnowledgeBase, KnowledgeBaseDocumentLink
from app.models.security import KnowledgeBasePermission

# ── [Fix-10] 缓存辅助函数 ────────────────────────────────────────────────────
_KB_CACHE_TTL = 300        # KB 元数据缓存 5 分钟
_PERM_CACHE_TTL = 120      # 权限缓存 2 分钟
_POLICY_CACHE_TTL = 600    # 安全策略缓存 10 分钟（进程内）

def _get_redis():
    """懒加载 Redis 客户端，避免循环导入。"""
    from app.core.redis import get_redis_client
    return get_redis_client()

def _kb_list_key(user_id: str) -> str:
    return f"kb:list:{user_id}"

def _kb_detail_key(kb_id: str) -> str:
    return f"kb:detail:{kb_id}"

def _perm_key(kb_id: str, user_id: str, level: str) -> str:
    return f"kb:perm:{kb_id}:{user_id}:{level}"

def _accessible_kbs_key(user_id: str) -> str:
    return f"kb:accessible:{user_id}"

def _invalidate_kb_cache(kb_id: str, owner_id: str | None = None):
    """KB 变更时主动失效相关缓存键。"""
    try:
        r = _get_redis()
        keys_to_del = [_kb_detail_key(kb_id)]
        if owner_id:
            keys_to_del += [_kb_list_key(owner_id), _accessible_kbs_key(owner_id)]
        r.delete(*keys_to_del)
    except Exception:
        pass  # 缓存失效失败不影响主流程


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

        # [Fix-10] 新建 KB 后失效该用户的列表缓存
        _invalidate_kb_cache(kb.id, owner_id=kb.owner_id)
        return kb

    async def get_kb(self, kb_id: str) -> KnowledgeBase:
        """[Fix-10] 先查 Redis 缓存，miss 时查 DB 并回填。"""
        try:
            r = _get_redis()
            cached = r.get(_kb_detail_key(kb_id))
            if cached:
                data = json.loads(cached)
                return KnowledgeBase(**data)
        except Exception:
            pass  # 缓存不可用时降级到 DB

        kb = await self.session.get(KnowledgeBase, kb_id)
        if not kb:
            raise NotFoundError(resource="knowledge_base", resource_id=kb_id)

        try:
            r = _get_redis()
            r.set(_kb_detail_key(kb_id), kb.model_dump_json(), ex=_KB_CACHE_TTL)
        except Exception:
            pass
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
        """Return a list of KB IDs that the user can read.
        [Fix-10] 结果缓存 2 分钟，减少每次 chat_stream 的权限查询开销。
        """
        cache_key = _accessible_kbs_key(current_user.id)
        try:
            r = _get_redis()
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        kbs = await self.list_kbs(current_user)
        result = [kb.id for kb in kbs]

        try:
            r = _get_redis()
            r.set(cache_key, json.dumps(result), ex=_PERM_CACHE_TTL)
        except Exception:
            pass
        return result

    async def check_kb_access(self, kb_id: str, user: User, level: str = "read") -> bool:
        """Check if user has specific access level to KB.
        [Fix-10] 权限结果缓存 2 分钟，admin 直接返回不走缓存。
        """
        if user.role == "admin":
            return True

        cache_key = _perm_key(kb_id, user.id, level)
        try:
            r = _get_redis()
            cached = r.get(cache_key)
            if cached is not None:
                return cached == "1"
        except Exception:
            pass

        kb = await self.session.get(KnowledgeBase, kb_id)
        if not kb:
            result = False
        elif kb.is_public and level == "read":
            result = True
        elif kb.owner_id == user.id:
            result = True
        else:
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
            result = any(
                (level == "read" and p.can_read)
                or (level == "write" and p.can_write)
                or (level == "manage" and p.can_manage)
                for p in perms
            )

        try:
            r = _get_redis()
            r.set(cache_key, "1" if result else "0", ex=_PERM_CACHE_TTL)
        except Exception:
            pass
        return result

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
        # [Fix-10] 文档关联变更后失效 KB 详情缓存
        _invalidate_kb_cache(kb_id)
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
            # [Fix-10] 文档解除关联后失效 KB 详情缓存
            _invalidate_kb_cache(kb_id)
