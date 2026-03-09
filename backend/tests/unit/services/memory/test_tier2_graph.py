from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_graph_store():
    with patch("app.services.memory.tier.graph_index.get_graph_store") as mock_get_store:
        mock_store = MagicMock()
        mock_store.driver = True  # Simulate Neo4j is available
        mock_get_store.return_value = mock_store
        yield mock_store


@pytest.fixture
def mock_llm_service():
    with patch("app.services.memory.tier.graph_index.get_llm_service") as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        yield mock_llm


@pytest.mark.asyncio
async def test_extract_and_store(mock_graph_store, mock_llm_service):
    """Verify that text is passed to LLM and resulting nodes/edges are stored in Neo4j."""
    from app.services.memory.tier.graph_index import GraphIndex

    # Mock LLM returning valid schema
    mock_llm_service.chat_complete = AsyncMock(return_value="""
    {
        "nodes": [{"id": "Alice", "label": "Person", "name": "Alice"}],
        "edges": [{"source": "Alice", "target": "Bob", "type": "KNOWS", "description": "friends"}]
    }
    """)

    index = GraphIndex()
    # Need to mock the internal store to be our mock_graph_store
    index.store = mock_graph_store

    await index.extract_and_store("doc_1", "Alice knows Bob.")

    # Assert import_subgraph is called correctly
    mock_graph_store.import_subgraph.assert_called_once()
    args, _ = mock_graph_store.import_subgraph.call_args
    assert len(args[0]) == 1  # exactly 1 node
    assert args[0][0]["id"] == "Alice"
    assert len(args[1]) == 1  # exactly 1 edge
    assert args[1][0]["type"] == "KNOWS"


@pytest.mark.asyncio
async def test_get_neighborhood(mock_graph_store):
    """Verify neighborhood query formatting and empty handling."""
    from app.services.memory.tier.graph_index import GraphIndex

    index = GraphIndex()
    index.store = mock_graph_store

    # Mock Cypher output (must handle run_in_executor mock if we were mocking that,
    # but here we mock index.store.query which is called inside lambda)
    mock_graph_store.query.return_value = [
        {"source": "Alice", "rel": "KNOWS", "target": "Bob", "descr": "Friends since 2020"},
        {"source": "Bob", "rel": "USES", "target": "Postgres", "descr": ""},
    ]

    results = await index.get_neighborhood(["Alice"])

    assert len(results) == 2
    assert "(Alice) -[KNOWS]-> (Bob)" in results[0]
    assert "Friends since 2020" in results[0]
    assert "(Bob) -[USES]-> (Postgres)" in results[1]

    # Verify Cypher was called with correct parameters
    mock_graph_store.query.assert_called_once()
    _cypher, params = mock_graph_store.query.call_args[0]
    assert "entities" in params
    assert params["entities"] == ["Alice"]


@pytest.mark.asyncio
async def test_get_neighborhood_empty_input(mock_graph_store):
    from app.services.memory.tier.graph_index import GraphIndex

    index = GraphIndex()
    index.store = mock_graph_store

    # Should not trigger DB
    results = await index.get_neighborhood([])
    assert results == []
    mock_graph_store.query.assert_not_called()
