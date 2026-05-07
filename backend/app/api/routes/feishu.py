from fastapi import APIRouter, Request, BackgroundTasks
from loguru import logger
import json
import subprocess
import os

router = APIRouter()

# ⚠️ 简单的后台任务：在这里可以异步调用 Kiro CLI / Deploy CLI，防止飞书 3 秒超时重试机制
def process_feishu_command_async(user_open_id: str, message_text: str):
    logger.info(f"🚀 [飞书 AIOps 任务启动] 正在为用户 {user_open_id} 执行指令: {message_text}")
    # 这里可以扩展：调用 Kiro CLI 或 cli.py 等！

@router.post("/webhook")
async def feishu_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        logger.debug(f"[Feishu Webhook Payload]: {json.dumps(body)}")
    except Exception as e:
        logger.error(f"Failed to parse Feishu webhook JSON: {e}")
        return {"code": 1, "msg": "Invalid JSON body"}

    # 1. 响应飞书首次配置 URL 时的握手 Challenge 校验
    if body.get("type") == "url_verification":
        challenge = body.get("challenge")
        logger.info(f"🟢 [Feishu Handshake] 收到飞书 URL 校验请求, Challenge: {challenge}")
        return {"challenge": challenge}

    # 2. 处理双向消息回调事件
    header = body.get("header", {})
    event_type = header.get("event_type")

    if event_type == "im.message.receive_v1":
        event = body.get("event", {})
        sender = event.get("sender", {})
        sender_id = sender.get("sender_id", {})
        open_id = sender_id.get("open_id")
        
        # 🌟 极客高亮打印：让用户在本地终端或生产日志里直接双击复制 Open ID！
        logger.warning("============================================================")
        logger.warning(f"🔥 [飞书 AIOps 探测成功] 收到您发送的手机消息！")
        logger.warning(f"👉 您的个人 User ID (Open ID) 为: {open_id}")
        logger.warning("============================================================")

        message = event.get("message", {})
        content_str = message.get("content", "{}")
        message_type = message.get("message_type")

        # 飞书文本消息 content 是 JSON 字符串：{"text": "your message"}
        text = ""
        try:
            content_json = json.loads(content_str)
            text = content_json.get("text", "").strip()
        except Exception:
            text = content_str

        logger.info(f"📱 [收到飞书单聊消息] 文本: '{text}' | 类型: {message_type}")

        # 异步处理：飞书 Webhook 必须在 3 秒内响应 200 OK，否则会判定超时并进行多次重试。
        # 我们使用 BackgroundTasks 将 AIOps 长任务放到后台，秒级返回 200 OK！
        background_tasks.add_task(process_feishu_command_async, open_id, text)

        return {"code": 0, "msg": "success"}

    return {"code": 0, "msg": "ignored event type"}
