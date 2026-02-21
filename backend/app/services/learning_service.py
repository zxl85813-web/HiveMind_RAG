from loguru import logger
from sqlmodel import select

from datetime import datetime
from pydantic import BaseModel
from app.core.database import async_session_factory
from app.models.chat import Message
from app.services.memory.memory_service import MemoryService

class Subscription(BaseModel):
    id: str
    topic: str
    is_active: bool = True
    created_at: datetime = datetime.now()

class TechDiscovery(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    category: str
    relevance_score: float
    discovered_at: datetime = datetime.now()

class LearningService:
    """
    Self-improving AI System and External Learning coordinator.
    """
    _mock_subscriptions = [
        {"id": "sub_1", "topic": "LangChain", "is_active": True, "created_at": datetime.now()},
        {"id": "sub_2", "topic": "React 19", "is_active": True, "created_at": datetime.now()},
    ]
    
    _mock_discoveries = [
        {
            "id": "disc_1",
            "title": "GPT-5 Architecture Leak?",
            "summary": "关于最新大模型架构的传闻分析，涉及多模态集成细节。",
            "url": "https://example.com/gpt5",
            "category": "paper",
            "relevance_score": 0.95,
            "discovered_at": datetime.now()
        },
        {
            "id": "disc_2",
            "title": "HiveMind v2.0 Released",
            "summary": "HiveMind 框架发布重大更新，支持分布式 Agent 协同。",
            "url": "https://github.com/hivemind/core",
            "category": "tool",
            "relevance_score": 0.88,
            "discovered_at": datetime.now()
        }
    ]

    @staticmethod
    async def get_subscriptions():
        return LearningService._mock_subscriptions

    @staticmethod
    async def add_subscription(topic: str):
        import uuid
        new_sub = {
            "id": f"sub_{uuid.uuid4().hex[:6]}",
            "topic": topic,
            "is_active": True,
            "created_at": datetime.now()
        }
        LearningService._mock_subscriptions.append(new_sub)
        return new_sub

    @staticmethod
    async def delete_subscription(sub_id: str):
        LearningService._mock_subscriptions = [s for s in LearningService._mock_subscriptions if s["id"] != sub_id]
        return True

    @staticmethod
    async def get_discoveries():
        return LearningService._mock_discoveries


    @staticmethod
    async def record_feedback(message_id: str, rating: int, comment: str | None = None):
        """Save raw feedback to DB."""
        async with async_session_factory() as session:
            msg = await session.get(Message, message_id)
            if msg:
                msg.rating = rating
                msg.feedback_text = comment
                session.add(msg)
                await session.commit()
                logger.info(f"Feedback recorded for msg {message_id}: {rating}")

    @staticmethod
    async def learn_from_feedback(message_id: str):
        """
        The Core Loop: Reflection & Knowledge Distillation.
        """
        async with async_session_factory() as session:
            ai_msg = await session.get(Message, message_id)
            if not ai_msg or not ai_msg.conversation_id:
                return

            # Get User Prompt (Previous message)
            # Simplification: Assume previous msg is user prompt
            query = (
                select(Message)
                .where(Message.conversation_id == ai_msg.conversation_id, Message.created_at < ai_msg.created_at)
                .order_by(Message.created_at.desc())
                .limit(1)
            )

            result = await session.exec(query)
            user_msg = result.first()

            if not user_msg:
                logger.warning("No context found for feedback analysis.")
                return

            # 1. Construct Reflection Prompt
            reflection_prompt = (
                "--- CONTEXT ---\n"
                f"User Query: {user_msg.content}\n"
                f"Your Response: {ai_msg.content}\n"
                f"User Feedback: {'POSITIVE' if ai_msg.rating > 0 else 'NEGATIVE'}"
                f" ({ai_msg.feedback_text or 'No comment'})\n"
            )

            # 2. Call LLM for Reflection (Mocked for now)
            # In production: response = await LLM.generate(reflection_prompt)
            reflection = await LearningService._mock_reflection(ai_msg.rating, user_msg.content)
            logger.debug("Reflection prompt built ({} chars)", len(reflection_prompt))

            # 3. Store Knowledge
            mem_service = MemoryService(user_id="system_learner")  # System-level memory
            await mem_service.add_memory(
                content=reflection,
                metadata={"type": "prompt_insight", "rating": ai_msg.rating, "source_msg": message_id},
            )

            logger.info(f"🧠 System Learned: {reflection[:50]}...")

    @staticmethod
    async def _mock_reflection(rating: int, query: str) -> str:
        """
        Mock LLM reflection logic.
        Reflect on WHY the response was good/bad.
        """
        if rating > 0:
            return (
                f"[SUCCESS PATTERN] When user asks about '{query[:10]}...',"
                " providing a step-by-step breakdown works well."
                " The structured format was appreciated."
            )
        else:
            return (
                f"[FAILURE ANALYSIS] User was unhappy with query '{query[:10]}...'."
                " Possible cause: The response was too verbose or lacked"
                " specific code examples. Action: Be more concise next time."
            )
