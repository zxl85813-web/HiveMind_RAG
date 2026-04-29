"""
Unit test conftest — 提供轻量级 mock fixtures。
所有外部依赖 (DB, LLM, Redis, Celery, Neo4j, Vector Store) 均被 mock。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Database Mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_session():
    """
    模拟 AsyncSession，覆盖常用的 ORM 操作。
    用法:
        async def test_something(mock_db_session):
            service = SomeService()
            # mock_db_session 会被注入到 get_db_session 依赖中
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()

    # exec() 返回一个可链式调用的 mock
    exec_result = MagicMock()
    exec_result.all.return_value = []
    exec_result.first.return_value = None
    exec_result.one_or_none.return_value = None
    exec_result.scalars.return_value = exec_result
    session.exec = AsyncMock(return_value=exec_result)
    session.execute = AsyncMock(return_value=exec_result)

    return session


@pytest.fixture
def mock_db_session_ctx(mock_db_session):
    """
    将 mock_db_session 包装为 async context manager，
    可直接 patch get_db_session。
    """
    async def _get_db():
        yield mock_db_session

    return _get_db


# ---------------------------------------------------------------------------
# LLM Mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """
    模拟 LLM Service，chat_complete 返回固定字符串，
    stream_chat 返回异步生成器。
    """
    llm = MagicMock()
    llm.chat_complete = AsyncMock(return_value="This is a mock LLM response.")

    async def _stream(*args, **kwargs):
        for chunk in ["Hello", " ", "World"]:
            yield chunk

    llm.stream_chat = MagicMock(return_value=_stream())
    return llm


# ---------------------------------------------------------------------------
# Redis Mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """模拟 Redis 客户端。"""
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=1)
    r.exists = AsyncMock(return_value=0)
    r.expire = AsyncMock(return_value=True)
    r.keys = AsyncMock(return_value=[])
    return r


# ---------------------------------------------------------------------------
# Celery Mock (eager mode)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_celery_app():
    """
    模拟 Celery app（eager 模式），任务同步执行不经过 broker。
    用法:
        def test_dispatch(mock_celery_app):
            mock_celery_app.send_task("some.task", args=[payload])
    """
    app = MagicMock()
    app.send_task = MagicMock(return_value=MagicMock(id="mock-task-id"))

    # eager 模式配置
    app.conf = MagicMock()
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True

    # AsyncResult mock
    async_result = MagicMock()
    async_result.id = "mock-task-id"
    async_result.status = "SUCCESS"
    async_result.result = None
    async_result.ready.return_value = True
    async_result.successful.return_value = True
    async_result.failed.return_value = False
    app.AsyncResult = MagicMock(return_value=async_result)

    return app


@pytest.fixture
def patch_celery_app(mock_celery_app):
    """
    Patch `app.core.celery_app.celery_app` 为 mock，
    适用于测试 IngestionDispatcher 等依赖 celery_app 的模块。
    """
    with patch("app.core.celery_app.celery_app", mock_celery_app):
        yield mock_celery_app


# ---------------------------------------------------------------------------
# Neo4j Mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_neo4j_store():
    """
    模拟 Neo4jStore，覆盖 query / add_triples / import_subgraph / close。
    用法:
        def test_graph(mock_neo4j_store):
            mock_neo4j_store.query.return_value = [{"name": "Alice"}]
    """
    store = MagicMock()
    store.driver = MagicMock()  # 标记为可用

    store.query = MagicMock(return_value=[])
    store.add_triples = MagicMock()
    store.import_subgraph = MagicMock()
    store.close = MagicMock()

    return store


@pytest.fixture
def patch_graph_store(mock_neo4j_store):
    """
    Patch `app.core.graph_store.get_graph_store` 返回 mock，
    适用于测试 GraphRetrievalStep / GraphIndex 等模块。
    """
    with patch("app.core.graph_store.get_graph_store", return_value=mock_neo4j_store):
        yield mock_neo4j_store


# ---------------------------------------------------------------------------
# Vector Store Mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vector_store():
    """
    模拟 BaseVectorStore 接口（add_documents / search / delete_documents / similarity_search）。
    默认 search 返回空列表，可通过 return_value 覆盖。
    用法:
        async def test_retrieval(mock_vector_store):
            mock_vector_store.search.return_value = [VectorDocument(...)]
    """
    store = MagicMock()
    store.add_documents = AsyncMock(return_value=[])
    store.search = AsyncMock(return_value=[])
    store.delete_documents = AsyncMock()
    store.similarity_search = AsyncMock(return_value=[])
    return store


@pytest.fixture
def make_vector_store():
    """
    工厂 fixture: 创建可定制的 Vector Store mock。
    用法:
        async def test_search(make_vector_store):
            store = make_vector_store(search_results=[doc1, doc2])
    """
    def _make(
        search_results: List[Any] | None = None,
        add_ids: List[str] | None = None,
    ):
        store = MagicMock()
        store.add_documents = AsyncMock(return_value=add_ids or [])
        store.search = AsyncMock(return_value=search_results or [])
        store.delete_documents = AsyncMock()
        store.similarity_search = AsyncMock(return_value=search_results or [])
        return store
    return _make


@pytest.fixture
def patch_vector_store(mock_vector_store):
    """
    Patch `app.core.vector_store.get_vector_store` 返回 mock，
    适用于测试 CacheService / RetrievalStep 等模块。
    """
    with patch("app.core.vector_store.get_vector_store", return_value=mock_vector_store):
        yield mock_vector_store


# ---------------------------------------------------------------------------
# Common Data Factories
# ---------------------------------------------------------------------------

@pytest.fixture
def make_user():
    """工厂 fixture: 创建模拟用户对象。"""
    def _make(user_id=None, username="testuser", role="user"):
        user = MagicMock()
        user.id = user_id or str(uuid4())
        user.username = username
        user.role = role
        user.department_id = None
        user.is_active = True
        user.created_at = datetime.now(timezone.utc)
        return user
    return _make


@pytest.fixture
def make_kb():
    """工厂 fixture: 创建模拟知识库对象。"""
    def _make(kb_id=None, name="Test KB", owner_id=None):
        kb = MagicMock()
        kb.id = kb_id or str(uuid4())
        kb.name = name
        kb.description = f"Description for {name}"
        kb.owner_id = owner_id or str(uuid4())
        kb.is_public = False
        kb.created_at = datetime.now(timezone.utc)
        kb.updated_at = datetime.now(timezone.utc)
        return kb
    return _make


@pytest.fixture
def make_document():
    """工厂 fixture: 创建模拟文档对象。"""
    def _make(doc_id=None, filename="test.pdf", status="completed"):
        doc = MagicMock()
        doc.id = doc_id or str(uuid4())
        doc.filename = filename
        doc.file_size = 1024
        doc.mime_type = "application/pdf"
        doc.status = status
        doc.created_at = datetime.now(timezone.utc)
        return doc
    return _make


@pytest.fixture
def make_conversation():
    """工厂 fixture: 创建模拟会话对象。"""
    def _make(conv_id=None, title="Test Conversation", user_id=None):
        conv = MagicMock()
        conv.id = conv_id or str(uuid4())
        conv.title = title
        conv.user_id = user_id or str(uuid4())
        conv.created_at = datetime.now(timezone.utc)
        conv.updated_at = datetime.now(timezone.utc)
        return conv
    return _make
