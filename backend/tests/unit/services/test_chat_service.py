import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest

@pytest.fixture
def chat_service():
    return ChatService()

@pytest.mark.asyncio
@pytest.mark.skip(reason="Complex Swarm mocking causes recursion in CI, requires refactoring test strategy")
async def test_chat_stream_radar_and_graph(chat_service):
    # Mock all the components used in chat_stream
    request = ChatRequest(message="database error", conversation_id="conv_1")
    
    with patch("app.services.chat_service.get_db_session") as mock_get_db, \
         patch("app.core.llm.get_llm_service") as mock_get_llm, \
         patch("app.services.memory.tier.abstract_index.abstract_index") as mock_radar_index, \
         patch("app.services.retrieval.get_retrieval_service") as mock_get_retriever, \
         patch("app.services.evaluation.multi_grader.MultiGraderEval") as mock_grader_class, \
         patch("app.services.memory.tier.graph_index.graph_index") as mock_graph_index:
        
        # Mock Grader
        mock_grader = AsyncMock()
        mock_grader.evaluate.return_value = MagicMock(composite_score=0.9, verdict="PASS", opinions=[])
        mock_grader_class.return_value = mock_grader
        
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.exec = AsyncMock()
        mock_session.execute = AsyncMock()
        
        # Setup mock_session.exec for chat messages
        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        mock_exec_result.first.return_value = None
        mock_session.exec.return_value = mock_exec_result
        
        # Setup mock_session.execute for security policy
        mock_execute_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_execute_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_execute_result

        async def mock_get_db_gen():
            yield mock_session
        mock_get_db.side_effect = mock_get_db_gen
        
        # Prevent real DB commit/rollback and add/flush/exec
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Setup mock_session.exec for chat messages to return empty
        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        mock_exec_result.first.return_value = None
        mock_session.exec.return_value = mock_exec_result
        
        # Mock Security Policy
        with patch("app.services.security_service.SecurityService.get_active_policy", new_callable=AsyncMock) as mock_policy:
            mock_policy.return_value = None
        
        # Mock LLM for Tags
        mock_llm = MagicMock()
        mock_llm.chat_complete = AsyncMock(return_value='{"tags": ["database"]}')
        async def mock_stream_gen(*args, **kwargs):
            yield "Hello"
            yield " World"
        mock_llm.stream_chat = MagicMock(return_value=mock_stream_gen())
        mock_get_llm.return_value = mock_llm
        
        # Mock Radar
        mock_radar_index.route_query.return_value = [{"title": "Memory1", "date": "2023-01-01", "type": "log"}]
        
        # Mock Graph
        mock_graph_index.get_neighborhood.return_value = AsyncMock(return_value=["(Alice) -[KNOWS]-> (Bob)"])()
        
        # Mock Retriever
        mock_retriever = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "Deep context"
        mock_retriever.retrieve.return_value = [mock_doc]
        mock_get_retriever.return_value = mock_retriever
        
        # Mock Cache
        with patch("app.services.cache_service.CacheService.get_cached_response", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = None
            
            # Mock Swarm
            from unittest.mock import PropertyMock
            with patch("app.services.chat_service._swarm", create=True) as mock_swarm, \
                 patch("app.services.cache_service.CacheService.set_cached_response", new_callable=AsyncMock) as mock_cache_set, \
                 patch("app.services.cache_service.TokenService.count_tokens") as mock_token_count, \
                 patch("app.core.tracing.ChatTracer") as mock_tracer_class:
                
                # Mock Tracer
                mock_tracer = MagicMock()
                mock_tracer.start_step = MagicMock()
                mock_tracer.get_trace_json.return_value = "{}"
                mock_tracer_class.return_value = mock_tracer
                
                mock_token_count.return_value = 10
                
                async def mock_swarm_gen(*args, **kwargs):
                    yield {"supervisor": {"next_step": "rag_agent", "task_refinement": "test"}}
                    msg = MagicMock()
                    msg.content = "Hello World"
                    yield {"rag_agent": {"messages": [msg]}}
                
                mock_swarm.invoke_stream.side_effect = mock_swarm_gen

        
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
                    data_str = r[6:].strip()
                    if data_str:
                        data = json.loads(data_str)
                        if "content" in data:
                            contents.append(data["content"])
                        elif "delta" in data:
                            contents.append(data["delta"])
                except json.JSONDecodeError as e:
                    print(f"JSON ERROR: {e} | DATA: {r}")
                    pass
        
        contents_str = "".join(contents)
        print(f"CONTENTS STR: {contents_str}")
        assert "Hello" in contents_str
        assert "World" in contents_str
