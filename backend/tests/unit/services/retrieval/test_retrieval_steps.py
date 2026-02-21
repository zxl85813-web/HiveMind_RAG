import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.retrieval.protocol import RetrievalContext
from app.services.retrieval.steps import QueryPreProcessingStep, HybridRetrievalStep, RerankingStep

@pytest.fixture
def mock_retrieval_context():
    ctx = RetrievalContext(query="test query", kb_ids=["kb1"])
    ctx.top_k = 5
    ctx.top_n = 2
    return ctx

@pytest.mark.asyncio
async def test_query_preprocessing_step(mock_retrieval_context):
    step = QueryPreProcessingStep()
    await step.execute(mock_retrieval_context)
    
    assert mock_retrieval_context.expanded_queries == ["test query"]
    assert any("[QueryProc]" in log for log in mock_retrieval_context.trace_log)

@pytest.mark.asyncio
async def test_hybrid_retrieval_step(mock_retrieval_context):
    mock_retrieval_context.expanded_queries = ["test query"]
    
    with patch("app.services.retrieval.steps.get_vector_store") as mock_get_store:
        mock_store = AsyncMock()
        # Returns a list of mock documents
        mock_doc1 = MagicMock(page_content="doc1 content")
        mock_doc2 = MagicMock(page_content="doc2 content")
        mock_store.search.return_value = [mock_doc1, mock_doc2, mock_doc1] # intentional duplicate
        mock_get_store.return_value = mock_store
        
        step = HybridRetrievalStep()
        await step.execute(mock_retrieval_context)
        
        # Should deduplicate by content, so only 2 candidates
        assert len(mock_retrieval_context.candidates) == 2
        mock_store.search.assert_called_once_with(
            query="test query",
            search_type="hybrid",
            k=5,
            collection_name="kb1"
        )

@pytest.mark.asyncio
async def test_reranking_step(mock_retrieval_context):
    mock_doc1 = MagicMock(page_content="doc1 content")
    mock_doc2 = MagicMock(page_content="doc2 content")
    mock_retrieval_context.candidates = [mock_doc1, mock_doc2]
    
    with patch("app.services.retrieval.steps.get_reranker") as mock_get_reranker:
        mock_reranker = AsyncMock()
        # Mock reranker returning only top 1
        mock_reranker.rerank.return_value = [mock_doc1]
        mock_get_reranker.return_value = mock_reranker
        
        step = RerankingStep()
        await step.execute(mock_retrieval_context)
        
        assert len(mock_retrieval_context.final_results) == 1
        assert mock_retrieval_context.final_results[0] == mock_doc1
        mock_reranker.rerank.assert_called_once_with(
            query="test query",
            documents=[mock_doc1, mock_doc2],
            top_n=2
        )

@pytest.mark.asyncio
async def test_reranking_step_empty_candidates(mock_retrieval_context):
    mock_retrieval_context.candidates = []
    
    with patch("app.services.retrieval.steps.get_reranker") as mock_get_reranker:
        step = RerankingStep()
        await step.execute(mock_retrieval_context)
        
        assert mock_retrieval_context.final_results == []
        mock_get_reranker.assert_not_called()
