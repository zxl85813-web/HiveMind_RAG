# Mock settings before app loading if necessary
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

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
        mock_instance.stream_chat = AsyncMock()  # You can define an async generator return if needed

        # Also patch the singleton getter
        with patch("app.core.llm.get_llm_service", return_value=mock_instance):
            yield mock_instance


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
