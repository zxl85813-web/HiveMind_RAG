def test_sentiment():
    # A simple test that might not use pytest-asyncio or proper mocks
    from backend.app.services.sentiment import SentimentService
    service = SentimentService()
    result = service.analyze_text("test")
    assert result is not None
