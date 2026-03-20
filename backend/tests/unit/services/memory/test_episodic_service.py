import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.episodic import EpisodicMemory
from app.services.memory.episodic_service import EpisodicMemoryService, EpisodeDistillResult

# 🧠 Objective: Verify Episodic Memory Service (Phase 2) distillation and storage logic.

@pytest.fixture
def service():
    return EpisodicMemoryService()

@pytest.fixture
def mock_messages():
    return [
        {"role": "user", "content": "How do I optimize Neo4j queries for large datasets?"},
        {"role": "assistant", "content": "You should use indexes and avoid Cartesian products in MATCH clauses."},
        {"role": "user", "content": "Can you give an example of an index creation?"},
        {"role": "assistant", "content": "Sure! Use `CREATE INDEX FOR (n:Person) ON (n.name)`."},
    ]

@pytest.fixture
def mock_distill():
    return EpisodeDistillResult(
        summary="Discussed Neo4j query optimization and indexing.",
        key_decisions=["Use indexes for name lookups"],
        topics=["Neo4j", "Optimization", "Indexing"],
        user_intent="Learn how to speed up graph queries"
    )

@pytest.mark.asyncio
async def test_store_episode_new(service, mock_messages, mock_distill):
    """Verify storing a NEW episode for a new conversation."""
    user_id = "user-123"
    conv_id = str(uuid.uuid4())

    # Mock LLM and Database
    with patch("app.services.memory.episodic_service.get_llm_service") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.chat_complete.return_value = '{"summary": "...", "key_decisions": [], "topics": [], "user_intent": "..."}'
        mock_get_llm.return_value = mock_llm

        with patch("app.services.memory.episodic_service.async_session_factory") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # await session.execute(stmt) -> returns a Result object
            mock_result = MagicMock()
            mock_session.execute.return_value = mock_result
            mock_result.scalar_one_or_none.return_value = None

            # Mock distillation
            with patch.object(service, "_distill_conversation", return_value=mock_distill):
                # Mock vectorization background task to avoid actual ChromaDB calls
                with patch.object(service, "_vectorize_episode", return_value=AsyncMock()):
                    
                    episode = await service.store_episode(user_id, conv_id, mock_messages)

                    assert episode is not None
                    assert episode.conversation_id == conv_id
                    assert episode.summary == mock_distill.summary
                    assert episode.user_id == user_id
                    
                    # Verify DB add was called
                    mock_session.add.assert_called_once()
                    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_store_episode_update(service, mock_messages, mock_distill):
    """Verify UPDATING an existing episode for the same conversation."""
    user_id = "user-123"
    conv_id = "existing-conv"
    
    existing_episode = EpisodicMemory(
        id="old-id", 
        user_id=user_id, 
        conversation_id=conv_id, 
        summary="Old summary"
    )

    with patch("app.services.memory.episodic_service.async_session_factory") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        
        # await session.execute(stmt) -> Result
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result
        mock_result.scalar_one_or_none.return_value = existing_episode

        with patch.object(service, "_distill_conversation", return_value=mock_distill):
            with patch.object(service, "_vectorize_episode", return_value=AsyncMock()):
                
                episode = await service.store_episode(user_id, conv_id, mock_messages)

                assert episode.id == "old-id"
                assert episode.summary == mock_distill.summary # Updated
                assert episode.temperature == 1.0 # Reset
                
                # Should NOT call session.add because it's an update
                mock_session.add.assert_not_called()
                mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_skip_low_value_session(service):
    """Verify that sessions with very few messages are skipped."""
    short_messages = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    
    episode = await service.store_episode("user-1", "conv-1", short_messages)
    assert episode is None
