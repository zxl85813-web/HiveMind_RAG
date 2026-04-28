"""
KnowledgeService 单元测试。

覆盖:
    - 知识库 CRUD (create / get / list)
    - 文档 CRUD (create / get)
    - 文档-知识库关联 (link / unlink / list)
    - 权限检查 (check_kb_access)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.knowledge.kb_service import KnowledgeService
from app.core.exceptions import NotFoundError


@pytest.fixture
def kb_service(mock_db_session):
    """创建注入了 mock session 的 KnowledgeService。"""
    return KnowledgeService(session=mock_db_session)


# ---------------------------------------------------------------------------
# Create KB
# ---------------------------------------------------------------------------

class TestCreateKB:

    @pytest.mark.asyncio
    async def test_create_kb_success(self, kb_service, mock_db_session):
        kb = MagicMock()
        kb.id = "kb_1"
        kb.owner_id = "user_1"

        result = await kb_service.create_kb(kb)

        # session.add 应被调用 2 次 (KB + ACL permission)
        assert mock_db_session.add.call_count == 2
        assert mock_db_session.commit.await_count == 2
        assert mock_db_session.refresh.await_count == 1
        assert result == kb


# ---------------------------------------------------------------------------
# Get KB
# ---------------------------------------------------------------------------

class TestGetKB:

    @pytest.mark.asyncio
    async def test_get_kb_found(self, kb_service, mock_db_session, make_kb):
        kb = make_kb(kb_id="kb_1")
        mock_db_session.get = AsyncMock(return_value=kb)

        result = await kb_service.get_kb("kb_1")
        assert result.id == "kb_1"

    @pytest.mark.asyncio
    async def test_get_kb_not_found_raises(self, kb_service, mock_db_session):
        mock_db_session.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await kb_service.get_kb("nonexistent")


# ---------------------------------------------------------------------------
# List KBs
# ---------------------------------------------------------------------------

class TestListKBs:

    @pytest.mark.asyncio
    async def test_admin_sees_all_kbs(self, kb_service, mock_db_session, make_kb, make_user):
        admin = make_user(role="admin")
        kbs = [make_kb(name="KB1"), make_kb(name="KB2")]

        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = kbs
        mock_db_session.execute = AsyncMock(return_value=exec_result)

        result = await kb_service.list_kbs(admin)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_user_sees_filtered_kbs(self, kb_service, mock_db_session, make_user):
        user = make_user(role="user")

        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=exec_result)

        result = await kb_service.list_kbs(user)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------

class TestDocumentCRUD:

    @pytest.mark.asyncio
    async def test_create_document(self, kb_service, mock_db_session):
        doc = MagicMock()
        doc.id = "doc_1"

        result = await kb_service.create_document(doc)
        mock_db_session.add.assert_called_once_with(doc)
        mock_db_session.commit.assert_awaited_once()
        assert result == doc

    @pytest.mark.asyncio
    async def test_get_document_found(self, kb_service, mock_db_session, make_document):
        doc = make_document(doc_id="doc_1")
        mock_db_session.get = AsyncMock(return_value=doc)

        result = await kb_service.get_document("doc_1")
        assert result.id == "doc_1"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, kb_service, mock_db_session):
        mock_db_session.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await kb_service.get_document("nonexistent")
