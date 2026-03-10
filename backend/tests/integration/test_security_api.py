import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user, get_db
from app.models.chat import User
from sqlmodel import SQLModel
from app.core.database import engine
from unittest.mock import AsyncMock, MagicMock

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
    
    mock_session = AsyncMock()
    # Mock database responses
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    app.dependency_overrides[get_db] = lambda: mock_session
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

def test_list_policies(client):
    response = client.get("/api/v1/security/policies")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["data"], list)

def test_get_detectors(client):
    response = client.get("/api/v1/security/detectors")
    assert response.status_code == 200
    data = response.json()
    assert "available_detectors" in data["data"]
    assert len(data["data"]["available_detectors"]) > 0

def test_audit_logs_admin_only(client, mock_user):
    # Test as admin (from fixture)
    response = client.get("/api/v1/security/audit/logs")
    assert response.status_code == 200
    
    # Test as non-admin
    mock_user.role = "user"
    response = client.get("/api/v1/security/audit/logs")
    assert response.status_code == 403
