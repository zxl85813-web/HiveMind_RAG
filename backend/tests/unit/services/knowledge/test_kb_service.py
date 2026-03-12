from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.models.chat import User
from app.models.knowledge import Document, KnowledgeBase, KnowledgeBaseDocumentLink
from app.services.knowledge.kb_service import KnowledgeService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    # Mock execute result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    session.execute.return_value = mock_result
    return session


@pytest.fixture
def kb_service(mock_session):
    return KnowledgeService(mock_session)


@pytest.mark.asyncio
async def test_create_kb(kb_service, mock_session):
    kb = KnowledgeBase(name="Test KB", owner_id="user_1", vector_collection="test_coll")

    # Run
    created_kb = await kb_service.create_kb(kb)

    # Assert
    assert created_kb.name == "Test KB"
    assert mock_session.add.call_count == 2  # KB + Permission
    mock_session.commit.assert_called()
    mock_session.refresh.assert_called_with(kb)


@pytest.mark.asyncio
async def test_get_kb_success(kb_service, mock_session):
    kb = KnowledgeBase(id="kb_1", name="Test KB", owner_id="user_1", vector_collection="test_coll")
    mock_session.get.return_value = kb

    result = await kb_service.get_kb("kb_1")
    assert result.id == "kb_1"
    mock_session.get.assert_called_with(KnowledgeBase, "kb_1")


@pytest.mark.asyncio
async def test_get_kb_not_found(kb_service, mock_session):
    mock_session.get.return_value = None

    with pytest.raises(NotFoundError):
        await kb_service.get_kb("non_existent")


@pytest.mark.asyncio
async def test_check_kb_access_admin(kb_service):
    user = User(id="user_admin", role="admin")
    has_access = await kb_service.check_kb_access("kb_1", user)
    assert has_access is True


@pytest.mark.asyncio
async def test_check_kb_access_owner(kb_service, mock_session):
    user = User(id="user_1", role="user")
    kb = KnowledgeBase(id="kb_1", owner_id="user_1", vector_collection="test_coll")
    mock_session.get.return_value = kb

    has_access = await kb_service.check_kb_access("kb_1", user)
    assert has_access is True


@pytest.mark.asyncio
async def test_check_kb_access_default_deny(kb_service, mock_session):
    user = User(id="user_2", role="user")
    kb = KnowledgeBase(id="kb_1", owner_id="user_1", is_public=False, vector_collection="test_coll")

    # Mock no ACL perms
    mock_session.get.return_value = kb
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_session.execute.return_value = mock_result

    has_access = await kb_service.check_kb_access("kb_1", user, level="read")
    assert has_access is False


@pytest.mark.asyncio
async def test_check_kb_access_public_read_only(kb_service, mock_session):
    user = User(id="user_2", role="user")
    kb = KnowledgeBase(id="kb_1", owner_id="user_1", is_public=True, vector_collection="test_coll")

    mock_session.get.return_value = kb
    # Mock no specific ACL perms
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_session.execute.return_value = mock_result

    can_read = await kb_service.check_kb_access("kb_1", user, level="read")
    assert can_read is True

    can_write = await kb_service.check_kb_access("kb_1", user, level="write")
    assert can_write is False


@pytest.mark.asyncio
async def test_link_document_to_kb(kb_service, mock_session):
    kb = KnowledgeBase(id="kb_1", owner_id="user_1", vector_collection="test_coll", version=1)
    doc = Document(id="doc_1", filename="test.txt", file_type="txt", file_size=100, storage_path="/tmp")

    # Mock existence checks
    async def mock_get(model, id_val):
        if model == KnowledgeBase:
            return kb
        if model == Document:
            return doc
        if model == KnowledgeBaseDocumentLink:
            return None
        return None

    mock_session.get.side_effect = mock_get

    link = await kb_service.link_document_to_kb("kb_1", "doc_1")

    assert link.knowledge_base_id == "kb_1"
    assert link.document_id == "doc_1"
    assert kb.version == 2
    mock_session.commit.assert_called()
