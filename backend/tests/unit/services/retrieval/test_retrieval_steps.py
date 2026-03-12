from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.retrieval.protocol import RetrievalContext
from app.services.retrieval.steps import HybridRetrievalStep, QueryPreProcessingStep, RerankingStep


@pytest.fixture
def mock_retrieval_context():
    ctx = RetrievalContext(query="test query", kb_ids=["kb1"])
    ctx.top_k = 5
    ctx.top_n = 2
    return ctx


@pytest.mark.asyncio
async def test_query_preprocessing_step(mock_retrieval_context):
    with patch("app.core.llm.get_llm_service") as mock_get_llm:
        mock_llm = AsyncMock()
        # Mock a valid JSON response as expected by the step
        mock_llm.chat_complete.return_value = (
            '{"intent": "fact", "rewritten_query": "expanded query", "hyde_document": "hyde doc", "keywords": ["test"]}'
        )
        mock_get_llm.return_value = mock_llm

        step = QueryPreProcessingStep()
        await step.execute(mock_retrieval_context)

        # Expect the original query AND rewritten/hyde queries to be present
        assert "test query" in mock_retrieval_context.expanded_queries
        assert "expanded query" in mock_retrieval_context.expanded_queries
        assert "hyde doc" in mock_retrieval_context.expanded_queries
        assert any("[QueryProc]" in log for log in mock_retrieval_context.trace_log)

        mock_llm.chat_complete.assert_called_once()


@pytest.mark.asyncio
async def test_hybrid_retrieval_step(mock_retrieval_context):
    mock_retrieval_context.expanded_queries = ["test query"]

    with patch("app.services.retrieval.steps.get_vector_store") as mock_get_store:
        mock_store = AsyncMock()
        # Returns a list of mock documents
        mock_doc1 = MagicMock(page_content="doc1 content")
        mock_doc2 = MagicMock(page_content="doc2 content")
        mock_store.search.return_value = [mock_doc1, mock_doc2, mock_doc1]  # intentional duplicate
        mock_get_store.return_value = mock_store

        step = HybridRetrievalStep()
        await step.execute(mock_retrieval_context)

        # Should deduplicate by content, so only 2 candidates
        assert len(mock_retrieval_context.candidates) == 2
        mock_store.search.assert_called_once_with(query="test query", search_type="hybrid", k=5, collection_name="kb1")


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
        mock_reranker.rerank.assert_called_once_with(query="test query", documents=[mock_doc1, mock_doc2], top_n=2)


@pytest.mark.asyncio
async def test_reranking_step_empty_candidates(mock_retrieval_context):
    mock_retrieval_context.candidates = []

    with patch("app.services.retrieval.steps.get_reranker") as mock_get_reranker:
        step = RerankingStep()
        await step.execute(mock_retrieval_context)

        assert mock_retrieval_context.final_results == []
        mock_get_reranker.assert_not_called()


@pytest.mark.asyncio
async def test_acl_filter_step_default_deny(mock_retrieval_context):
    from app.services.retrieval.steps import AclFilterStep

    mock_retrieval_context.user_id = "user_1"
    mock_retrieval_context.is_admin = False

    mock_doc = MagicMock()
    mock_doc.metadata = {"document_id": "doc_1"}
    mock_retrieval_context.candidates = [mock_doc]

    with (
        patch("app.services.retrieval.steps.async_session_factory") as mock_db,
        patch("app.auth.permissions.has_document_permission") as mock_has_perm,
    ):

        mock_session_instance = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session_instance

        # User exists
        mock_user = MagicMock(username="test", role="user", department_id="dept1")
        mock_session_instance.get.return_value = mock_user

        # Explicitly deny access (default deny behavior)
        mock_has_perm.return_value = False

        step = AclFilterStep()
        await step.execute(mock_retrieval_context)

        # The candidate should be filtered out
        assert len(mock_retrieval_context.candidates) == 0
        mock_has_perm.assert_called_once()
