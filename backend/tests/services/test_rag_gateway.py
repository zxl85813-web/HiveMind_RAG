import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.rag_gateway import RAGGateway
from app.schemas.knowledge_protocol import KnowledgeFragment, KnowledgeResponse

@pytest.fixture
def rag_gateway():
    # Clear circuit breaker state between tests
    RAGGateway._circuit_breakers = {}
    return RAGGateway()

@pytest.mark.asyncio
async def test_retrieve_success(rag_gateway):
    """验证正常情况下的多 KB 并行检索"""
    mock_read_service = AsyncMock()
    mock_read_service.retrieve_from_kb.return_value = (
        [KnowledgeFragment(content="test", kb_id="kb1", source_id="s1", chunk_index=1, score=0.9)],
        ["trace 1"]
    )
    
    # 手动注入 mock
    rag_gateway.read_service = mock_read_service
    
    async def mock_execute(dep, fn):
        return await fn()
    
    # Mock breaker_manager to just pass through
    with patch("app.services.rag_gateway.breaker_manager.execute", side_effect=mock_execute), \
         patch("app.services.rag_gateway.choose_topology_path") as mock_topo, \
         patch("app.services.rag_gateway.fire_and_forget_trace"):
        
        mock_topo.return_value = MagicMock(mode="monolith", path="default")
        
        response = await rag_gateway.retrieve(query="hi", kb_ids=["kb1", "kb2"])
        
        assert len(response.fragments) == 2
        assert response.total_found == 2
        assert mock_read_service.retrieve_from_kb.call_count == 2

@pytest.mark.asyncio
async def test_circuit_breaker_tripping(rag_gateway):
    """验证熔断器在连续失败后开启"""
    mock_read_service = AsyncMock()
    mock_read_service.retrieve_from_kb.side_effect = Exception("Connection Timeout")
    rag_gateway.read_service = mock_read_service
    
    async def mock_execute(dep, fn):
        return await fn()
    
    # 模拟 breaker_manager 的异常传导
    with patch("app.services.rag_gateway.breaker_manager.execute", side_effect=mock_execute), \
         patch("app.services.rag_gateway.choose_topology_path"), \
         patch("app.services.rag_gateway.fire_and_forget_trace"):
        
        # Trigger 3 failures to trip the circuit (max_failures=3)
        for _ in range(3):
            await rag_gateway.retrieve(query="fail", kb_ids=["bad_kb"])
        
        # 4th call should be blocked by circuit breaker
        response = await rag_gateway.retrieve(query="blocked", kb_ids=["bad_kb"])
        
        assert any("Circuit Breaker OPEN" in w for w in response.warnings)
        assert len(response.fragments) == 0
        assert mock_read_service.retrieve_from_kb.call_count == 3

@pytest.mark.asyncio
async def test_partial_failure_handling(rag_gateway):
    """验证部分 KB 失败时，系统仍能返回其他 KB 的结果"""
    async def side_effect(kb_id, **kwargs):
        if kb_id == "error_kb":
            raise Exception("Internal DB Error")
        return ([KnowledgeFragment(content="ok", kb_id=kb_id, source_id="s1", chunk_index=0, score=0.5)], ["trace"])

    mock_read_service = AsyncMock()
    mock_read_service.retrieve_from_kb.side_effect = side_effect
    rag_gateway.read_service = mock_read_service
    
    async def mock_execute(dep, fn):
        return await fn()
    
    with patch("app.services.rag_gateway.breaker_manager.execute", side_effect=mock_execute), \
         patch("app.services.rag_gateway.choose_topology_path"), \
         patch("app.services.rag_gateway.fire_and_forget_trace"):
        
        response = await rag_gateway.retrieve(query="partial", kb_ids=["ok_kb", "error_kb"])
        
        assert len(response.fragments) == 1
        assert response.fragments[0].kb_id == "ok_kb"
        assert any("error_kb" in w for w in response.warnings)

@pytest.mark.asyncio
async def test_prefetch_caching(rag_gateway):
    """验证预取功能是否成功写入缓存"""
    mock_response = KnowledgeResponse(
        query="prefetch",
        fragments=[KnowledgeFragment(content="cached text", kb_id="kb1", source_id="s1", chunk_index=0, score=1.0)],
        total_found=1,
        processing_time_ms=10,
        step_traces=["trace"]
    )
    
    # Mock retrieve to return fixed response
    rag_gateway.retrieve = AsyncMock(return_value=mock_response)
    
    with patch("app.services.cache_service.CacheService.set_intent_cache") as mock_set_cache:
        await rag_gateway.prefetch(query="prefetch", kb_ids=["kb1"], user_id="user_123")
        
        mock_set_cache.assert_called_once()
        args, kwargs = mock_set_cache.call_args
        assert kwargs["session_id"] == "user_123"
        assert "cached text" in kwargs["data"]["context_data"]
