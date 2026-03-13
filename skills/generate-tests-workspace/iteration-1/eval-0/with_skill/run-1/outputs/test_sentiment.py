# backend/tests/unit/services/test_sentiment.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.sentiment import SentimentService
from backend.app.schemas.sentiment import SentimentResponse

@pytest.mark.asyncio
class TestSentimentService:
    
    # 1. Contract View: Success Flow
    async def test_analyze_sentiment_success_returns_schema(self, db_session):
        service = SentimentService(db_session)
        
        # Mocking LLM Call as per Mock Decision Tree
        with patch("backend.app.infrastructure.llm.LLMClient.call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"label": "positive", "score": 0.9}
            
            result = await service.analyze_text("This project is awesome!")
            
            assert isinstance(result, SentimentResponse)
            assert result.label == "positive"
            mock_llm.assert_called_once()

    # 2. Logic/Resilience View: Error Handling
    async def test_analyze_sentiment_llm_failure_raises_exception(self, db_session):
        service = SentimentService(db_session)
        
        with patch("backend.app.infrastructure.llm.LLMClient.call", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("API Down")
            
            with pytest.raises(Exception) as exc:
                await service.analyze_text("Hello")
            
            assert "API Down" in str(exc.value)
