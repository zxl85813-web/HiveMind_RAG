import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest

@pytest.fixture
def chat_service():
    return ChatService()

@pytest.mark.asyncio
async def test_chat_stream_radar_and_graph(chat_service):
    # Mock all the components used in chat_stream
    request = ChatRequest(message="database error", conversation_id="conv_1")
    
    with patch("app.services.chat_service.get_db_session") as mock_get_db, \
         patch("app.core.llm.get_llm_service") as mock_get_llm, \
         patch("app.services.memory.tier.abstract_index.abstract_index") as mock_abstract_index, \
         patch("app.services.retrieval.get_retrieval_service") as mock_get_retriever, \
         patch("app.services.memory.tier.graph_index.graph_index") as mock_graph_index:
        
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.exec.return_value = MagicMock(all=lambda: [])
        async def mock_get_db_gen():
            yield mock_session
        mock_get_db.side_effect = mock_get_db_gen
        
        # Mock LLM for Tags
        mock_llm = MagicMock()
        mock_llm.chat_complete = AsyncMock(return_value='{"tags": ["database"]}')
        async def mock_stream_gen(*args, **kwargs):
            yield "Hello"
            yield " World"
        mock_llm.stream_chat = MagicMock(return_value=mock_stream_gen())
        mock_get_llm.return_value = mock_llm
        
        # Mock Radar
        mock_abstract_index.route_query.return_value = [{"title": "Memory1", "date": "2023-01-01", "type": "log"}]
        
        # Mock Graph
        mock_graph_index.get_neighborhood.return_value = ["(Alice) -[KNOWS]-> (Bob)"]
        
        # Mock Retriever
        mock_retriever = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "Deep context"
        mock_retriever.retrieve.return_value = [mock_doc]
        mock_get_retriever.return_value = mock_retriever
        
        
        # Run generator
        responses = []
        async for chunk in ChatService.chat_stream(request, "user_1"):
            responses.append(chunk)
            
        print(f"DEBUG RESPONSES: {responses}")
        
        # Ensure we received status updates and stream content
        contents = []
        for r in responses:
            if r.startswith("data: ") and r.strip() != "data: [DONE]":
                try:
                    data = json.loads(r[6:].strip())
                    if "content" in data:
                        contents.append(data["content"])
                    elif "delta" in data:
                        contents.append(data["delta"])
                except json.JSONDecodeError:
                    pass
        
        contents_str = "".join(contents)
        assert "⚡ 雷达定位到" in contents_str
        assert "🕸️ 图谱扩展了" in contents_str
        assert "Hello" in contents_str
        assert "World" in contents_str
