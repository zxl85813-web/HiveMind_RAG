import asyncio
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest
from unittest.mock import patch, MagicMock, AsyncMock

async def run():
    request = ChatRequest(message="database error")
    with patch("app.services.chat_service.get_db_session") as mock_get_db, \
         patch("app.core.llm.get_llm_service") as mock_get_llm, \
         patch("app.services.memory.tier.abstract_index.abstract_index") as mock_abstract_index, \
         patch("app.services.retrieval.get_retrieval_service") as mock_get_retriever, \
         patch("app.services.memory.tier.graph_index.graph_index") as mock_graph_index:
        
        mock_session = AsyncMock()
        async def mock_get_db_gen():
            yield mock_session
        mock_get_db.side_effect = mock_get_db_gen
        
        mock_llm = MagicMock()
        mock_llm.chat_complete = AsyncMock(return_value='{"tags": ["database"]}')
        async def mock_stream_gen(*args, **kwargs):
            yield "Hello"
            yield " World"
        mock_llm.chat_stream = MagicMock(return_value=mock_stream_gen())
        mock_get_llm.return_value = mock_llm
        
        mock_abstract_index.route_query.return_value = [{"title": "Memory1", "date": "2023-01-01", "type": "log"}]
        mock_graph_index.get_neighborhood.return_value = ["(Alice) -[KNOWS]-> (Bob)"]
        
        mock_retriever = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "Deep context"
        mock_retriever.retrieve.return_value = [mock_doc]
        mock_get_retriever.return_value = mock_retriever
        
        try:
            async for chunk in ChatService.chat_stream(request, "user_1"):
                print("CHUNK:", chunk.strip())
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(run())
