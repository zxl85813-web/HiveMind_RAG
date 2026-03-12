from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.api.deps import get_current_user
from app.core.database import engine
from app.main import app
from app.models.chat import User


@pytest.fixture
def mock_user():
    return User(id="user_admin", username="admin", email="admin@example.com", role="admin")


@pytest.fixture
async def client(mock_user):
    # Create tables in the in-memory DB
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.routes.memory.MemoryService")
async def test_get_role_memory(mock_mem_svc, client, mock_user):
    mock_instance = mock_mem_svc.return_value
    mock_instance._load_role_memory.return_value = {"role_id": "test_role", "terms": {"test": "val"}}
    
    response = client.get("/api/v1/memory/roles/test_role")
    assert response.status_code == 200
    data = response.json()
    assert data["role_id"] == "test_role"


@pytest.mark.asyncio
@patch("app.api.routes.memory.MemoryService")
async def test_update_role_memory(mock_mem_svc, client, mock_user):
    mock_instance = mock_mem_svc.return_value
    
    response = client.put("/api/v1/memory/roles/test_role", json={"role_id": "test_role", "terms": {"t": "v"}})
    assert response.status_code == 200
    mock_instance.save_role_memory.assert_called_once()
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
@patch("app.api.routes.memory.MemoryService")
async def test_get_personal_memory(mock_mem_svc, client, mock_user):
    mock_instance = mock_mem_svc.return_value
    mock_instance._load_personal_memory.return_value = {"user_id": mock_user.id, "language": "zh"}
    
    response = client.get("/api/v1/memory/personal")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == mock_user.id


@pytest.mark.asyncio
@patch("app.api.routes.memory.MemoryService")
async def test_update_personal_memory(mock_mem_svc, client, mock_user):
    mock_instance = mock_mem_svc.return_value
    
    response = client.put("/api/v1/memory/personal", json={"user_id": mock_user.id, "language": "en"})
    assert response.status_code == 200
    mock_instance.save_personal_memory.assert_called_once()
    assert response.json()["status"] == "success"
