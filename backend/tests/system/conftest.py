import pytest
from unittest.mock import AsyncMock, patch
from app.services.llm_gateway import GatewayResponse
import json

@pytest.fixture
def mock_llm():
    with patch("app.services.agents.supervisor.llm_gateway.call_tier", new_callable=AsyncMock) as mock_sup:
        with patch("app.services.agents.workers.research_agent.llm_gateway.call_tier", new_callable=AsyncMock) as mock_res:
            with patch("app.services.agents.workers.code_agent.llm_gateway.call_tier", new_callable=AsyncMock) as mock_code:
                with patch("app.services.agents.workers.reviewer_agent.llm_gateway.call_tier", new_callable=AsyncMock) as mock_rev:
                    yield {
                        "supervisor": mock_sup,
                        "research": mock_res,
                        "code": mock_code,
                        "reviewer": mock_rev
                    }

@pytest.fixture
async def clean_test_db():
    from app.core.database import init_db, engine
    from sqlmodel import SQLModel
    
    # Force use of a test DB URI
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./system_test.db"
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    
    # Optional cleanup
    if os.path.exists("./system_test.db"):
        try: os.remove("./system_test.db")
        except: pass
