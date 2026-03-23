import pytest
from app.models.observability import RAGQueryTrace

def test_rag_query_trace_new_fields():
    # This should fail initially because fields are missing
    trace = RAGQueryTrace(
        query="test",
        prefetch_hit=True,
        intent_predicted="chat",
        time_budget_used=150
    )
    assert trace.prefetch_hit is True
    assert trace.intent_predicted == "chat"
    assert trace.time_budget_used == 150

def test_intent_cache_model_fields():
    # This should fail initially because the module is missing
    from app.models.intent import IntentCache
    from datetime import datetime, timedelta
    cache = IntentCache(
        query_hash="abc",
        predicted_intent="chat",
        raw_results={"docs": [1, 2, 3]},
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    assert cache.query_hash == "abc"
    assert cache.predicted_intent == "chat"
    assert cache.raw_results == {"docs": [1, 2, 3]}
