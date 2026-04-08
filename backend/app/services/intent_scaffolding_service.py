"""
Intent Scaffolding Service — Predictive Intent Detection & Speculative Retrieval.
Part of Task 2: Latency Optimization (REQ-013 / DES-013).

This service analyzes partial user input (from WebSocket) to predict intent
before the full message is sent. Early detection allows triggering RAG prefetch.
"""

from typing import Literal
from loguru import logger
from pydantic import BaseModel

from app.core.algorithms.classification import classifier_service
class IntentPrediction(BaseModel):
    intent: str
    confidence: float
    tier: str
    is_prefetch_triggered: bool = False

class IntentScaffoldingService:
    """
    Implements Intent Scaffolding (Phase 1 Reconstruction).
    Reduces Perceived Latency by 200-500ms.
    """
    
    INTENTS = {
        "rag": "搜索,查找,文档,知识库,什么是,如何,解释,search,find,tell me about,what is",
        "code": "代码,调试,python,javascript,编写,bug,fix,how to code,script",
        "agent_control": "切换,清理,重置,设置,switch,reset,clear,settings",
        "general": "你好,打个招呼,闲聊,hello,hi,chat"
    }

    def __init__(self):
        # Minimum characters to start prediction
        self.min_chars = 6
        # Track session-level prefetch status to avoid double-triggering
        self._triggered_sessions: set[str] = set()

    async def predict_and_scaffold(
        self, 
        partial_text: str, 
        session_id: str
    ) -> IntentPrediction | None:
        """
        Analyze partial text and trigger prefetch if confident.
        """
        if len(partial_text) < self.min_chars:
            return None

        # Tiered Cascade Classification
        intent, confidence, tier = await classifier_service.classify_cascade(
            text=partial_text,
            categories=self.INTENTS,
            default="general"
        )

        prediction = IntentPrediction(
            intent=intent,
            confidence=confidence,
            tier=tier
        )

        # Trigger Speculative Retrieval for RAG/Code if confidence is high (Rule or High T1)
        if intent in ["rag", "code"] and tier in ["rule", "vector"]:
            if session_id not in self._triggered_sessions:
                logger.info(f"🛰️ [Scaffolding] Speculative Prefetch Triggered: {intent} (via {tier})")
                
                # In a real system, this would call RAGGateway.prefetch()
                # or similar async task to warm up embeddings and vector search cache.
                try:
                    await self._trigger_prefetch(partial_text, intent, session_id)
                    prediction.is_prefetch_triggered = True
                    self._triggered_sessions.add(session_id)
                except Exception as e:
                    logger.warning(f"Prefetch trigger failed: {e}")

        return prediction

    async def _trigger_prefetch(self, text: str, intent: str, session_id: str):
        """
        Trigger actual prefetch via RAGGateway.
        Part of M5.2.1 speculative optimization.
        """
        from app.services.rag_gateway import RAGGateway
        logger.info(f"🛰️ [Scaffolding] Prefetching for {intent}: '{text[:15]}...'")
        
        # Instantiate RAGGateway (it uses internal singleton logic anyway)
        gateway = RAGGateway()
        # In a real session, kb_ids would come from user config. 
        # For REQ-013 proof-of-concept, we use "default".
        await gateway.prefetch(query=text, kb_ids=["default"], user_id=session_id)

    def clear_session(self, session_id: str):
        """Cleanup after a message is finalized."""
        if session_id in self._triggered_sessions:
            self._triggered_sessions.remove(session_id)

# Singleton instance
intent_scaffolding_service = IntentScaffoldingService()
