# Mock settings before app loading if necessary
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Early patch to prevent real API initialization during import
from unittest.mock import MagicMock, patch
patch("app.core.embeddings.ZhipuAI", return_value=MagicMock()).start()

from app.main import app

# --- Pytest Fixtures ---


@pytest.fixture(scope="session")
def api_client():
    """Returns a FastAPI TestClient instance."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_llm_service():
    """
    A unified fixture to mock the LLM Service so tests do not consume real tokens.
    Usage:
    def test_logic(mock_llm_service):
        mock_llm_service.chat_complete.return_value = '{"test": "ok"}'
    """
    with patch("app.core.llm.LLMService") as mock_llm_class:
        mock_instance = mock_llm_class.return_value
        mock_instance.chat_complete = AsyncMock()
        mock_instance.stream_chat = AsyncMock()
        mock_instance.client = MagicMock()
        # Setup instructor-compatible async mock
        mock_instance.client.chat.completions.create = AsyncMock()
        # You can define an async generator return if needed

        # Also patch the singleton getter
        with patch("app.core.llm.get_llm_service", return_value=mock_instance), \
             patch("instructor.from_openai", return_value=mock_instance.client):
            yield mock_instance


@pytest.fixture
def mock_embedding_service():
    """Mocks the Embedding Service and the underlying ZhipuAI client."""
    with patch("app.core.embeddings.ZhipuAI") as mock_zhipu:
        mock_zhipu.return_value = MagicMock()
        
        with patch("app.core.embeddings.ZhipuEmbeddingService") as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.embed_query.return_value = [0.1] * 1024
            mock_instance.embed_documents.return_value = [[0.1] * 1024]

            # Patch get_embedding_service in all locations where it's imported
            with patch("app.core.embeddings.get_embedding_service", return_value=mock_instance), \
                 patch("app.core.algorithms.routing.get_embedding_service", return_value=mock_instance):
                yield mock_instance


@pytest.fixture(autouse=True)
def _auto_mock_embeddings(mock_embedding_service):
    """Automatically mock embeddings for all tests."""
    pass


@pytest.fixture(autouse=True)
def wipe_in_memory_stores():
    """
    Automatically wipe purely in-memory data structures between test runs
    to prevent cross-test pollution.
    """
    from app.services.memory.tier.abstract_index import abstract_index

    # Reset singleton state
    abstract_index.doc_store.clear()
    abstract_index.tag_index.clear()
    abstract_index.type_index.clear()
    abstract_index.date_index.clear()
    yield
