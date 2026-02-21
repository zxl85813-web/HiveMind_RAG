"""
API Router — aggregates all route modules.
"""

from fastapi import APIRouter

from app.api.routes import agents, chat, health, knowledge, learning, websocket, generation, memory

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
router.include_router(learning.router, prefix="/learning", tags=["External Learning"])
router.include_router(generation.router, prefix="/generation", tags=["Generation"])
router.include_router(memory.router, prefix="/memory", tags=["Memory"])
