"""
WebSocket endpoint — persistent connection for proactive push notifications.
"""

from fastapi import APIRouter, WebSocket

router = APIRouter()


from starlette.websockets import WebSocketDisconnect

from app.services.ws_manager import ws_manager


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

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id)
    except Exception:
        await ws_manager.disconnect(websocket, user_id)
