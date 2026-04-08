"""
WebSocket endpoint — persistent connection for proactive push notifications.
"""

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.services.ws_manager import ws_manager

router = APIRouter()


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket connection for proactive push features.
    """
    # 1. Accept and register (Auth TODO)
    user_id = "test_user"  # Fallback for now
    await ws_manager.connect(websocket, user_id)

    try:
        while True:
            # 2. Listen for incoming messages (e.g. ping, subscribe)
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "subscribe":
                channel = data.get("channel")
                if channel:
                    ws_manager.subscribe(user_id, channel)
                    await websocket.send_json({"type": "subscribed", "channel": channel})
            
            # 🛰️ [M5.2.1] Intent Scaffolding: On-the-fly intent prediction
            elif data.get("type") == "partial_input":
                content = data.get("content", "")
                from app.services.intent_scaffolding_service import intent_scaffolding_service
                
                prediction = await intent_scaffolding_service.predict_and_scaffold(
                    partial_text=content,
                    session_id=user_id
                )
                
                if prediction:
                    await websocket.send_json({
                        "type": "intent_prediction",
                        "intent": prediction.intent,
                        "confidence": prediction.confidence,
                        "tier": prediction.tier,
                        "prefetched": prediction.is_prefetch_triggered
                    })
            
            # 🔥 [M5.2.2] Message Finalized (Clear prefetch flags)
            elif data.get("type") == "message_final":
                from app.services.intent_scaffolding_service import intent_scaffolding_service
                intent_scaffolding_service.clear_session(user_id)

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id)
    except Exception:
        await ws_manager.disconnect(websocket, user_id)
