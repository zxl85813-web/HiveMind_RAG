import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from skills.architectural_mapping.scripts.index_architecture import ArchitectureIndexer

@pytest.fixture
def mock_indexer():
    with patch("neo4j.GraphDatabase.driver") as mock_driver:
        indexer = ArchitectureIndexer("bolt://mock", "user", "pass")
        # Mock run_query to avoid real DB calls
        indexer.run_query = MagicMock()
        return indexer

def test_index_requirements_parsing(mock_indexer):
    # Mocking Path.glob and open
    with patch("pathlib.Path.glob") as mock_glob, \
         patch("builtins.open", patch("builtins.open", MagicMock())):
        
        # Setup a mock requirement file
        mock_file = MagicMock(spec=Path)
        mock_file.stem = "REQ-001-test"
        mock_file.relative_to.return_value = "docs/requirements/REQ-001-test.md"
        mock_glob.return_value = [mock_file]
        
        # Mock file content
        with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="# REQ-001: Sample Req")))))):
            mock_indexer.index_requirements()
        
        # Verify run_query was called with correct data
        mock_indexer.run_query.assert_called()
        args, kwargs = mock_indexer.run_query.call_args
        assert "Requirement" in args[0]
        assert kwargs["id"] == "REQ-001"
        assert kwargs["title"] == "Sample Req"

def test_clear_graph_logic(mock_indexer):
    mock_indexer.clear_graph()
    mock_indexer.run_query.assert_called_with("MATCH (n:ArchNode) DETACH DELETE n")
