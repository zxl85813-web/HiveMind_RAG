"""
Ingestion Progress Service — 文档摄入进度推送。

架构：
  Celery Worker ──publish──► Redis Pub/Sub Channel
                                      │
                              SSE Generator (FastAPI)
                                      │
                              前端 EventSource

Channel 命名规则：
  ingestion:batch:{batch_id}   — 批次级别进度（推荐前端订阅）
  ingestion:doc:{doc_id}       — 单文档级别进度（可选）

事件格式（JSON）：
  {
    "event":      "progress" | "file_done" | "file_failed" | "batch_done",
    "batch_id":   "...",
    "doc_id":     "...",          # file_done / file_failed 时有值
    "filename":   "...",          # 文件名，用于 UI 展示
    "folder_path":"...",          # 文件夹路径
    "total":      100,            # 批次总文件数
    "completed":  42,             # 已完成数
    "failed":     3,              # 失败数
    "percent":    42.0,           # 完成百分比
    "status":     "processing",   # processing | completed | partial_failed
    "message":    "...",          # 可读描述
    "ts":         1714200000.0,   # Unix 时间戳
  }
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger


# ── Redis Channel 工具 ────────────────────────────────────────────────────────

def batch_channel(batch_id: str) -> str:
    return f"ingestion:batch:{batch_id}"

def doc_channel(doc_id: str) -> str:
    return f"ingestion:doc:{doc_id}"


# ── 发布进度事件（Celery Worker 侧调用，同步）────────────────────────────────

def publish_progress(
    batch_id: str,
    event: str,
    total: int,
    completed: int,
    failed: int,
    doc_id: str | None = None,
    filename: str | None = None,
    folder_path: str | None = None,
    message: str | None = None,
) -> None:
    """
    从 Celery Worker（同步上下文）向 Redis 发布进度事件。
    Redis 不可用时静默忽略，不影响主流程。
    """
    try:
        from app.core.redis import get_redis_client
        r = get_redis_client()

        percent = round(completed / max(total, 1) * 100, 1)

        if completed + failed >= total:
            status = "completed" if failed == 0 else "partial_failed"
        else:
            status = "processing"

        payload: dict[str, Any] = {
            "event": event,
            "batch_id": batch_id,
            "doc_id": doc_id,
            "filename": filename,
            "folder_path": folder_path,
            "total": total,
            "completed": completed,
            "failed": failed,
            "percent": percent,
            "status": status,
            "message": message or _default_message(event, filename, completed, total),
            "ts": time.time(),
        }

        channel = batch_channel(batch_id)
        r.publish(channel, json.dumps(payload, ensure_ascii=False))

        # 同时发布到单文档频道（可选订阅）
        if doc_id:
            r.publish(doc_channel(doc_id), json.dumps(payload, ensure_ascii=False))

    except Exception as e:
        logger.debug(f"[Progress] Publish failed (non-critical): {e}")


def _default_message(event: str, filename: str | None, completed: int, total: int) -> str:
    name = filename or "文件"
    if event == "file_done":
        return f"✅ {name} 处理完成 ({completed}/{total})"
    if event == "file_failed":
        return f"❌ {name} 处理失败 ({completed}/{total})"
    if event == "batch_done":
        return f"🎉 批次处理完成，共 {total} 个文件"
    return f"⏳ 正在处理 {name}... ({completed}/{total})"


# ── SSE 生成器（FastAPI 侧调用，异步）────────────────────────────────────────

async def stream_batch_progress(
    batch_id: str,
    timeout_sec: int = 1800,   # 最长等待 30 分钟
    poll_interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """
    订阅 Redis Pub/Sub，将进度事件转为 SSE 格式推送给前端。

    降级策略：
      - Redis Pub/Sub 可用 → 实时推送（延迟 < 100ms）
      - Redis 不可用 → 轮询数据库（每 2 秒查一次 IngestionBatch）
    """
    # 先推送一次当前快照（让前端立即看到初始状态）
    snapshot = await _get_batch_snapshot(batch_id)
    if snapshot:
        yield _sse_event("progress", snapshot)

    # 尝试 Redis Pub/Sub
    try:
        from app.core.redis import get_redis_client
        import redis as redis_lib

        r = get_redis_client()
        # 检查是否是真实 Redis（MockRedis 没有 pubsub 方法）
        if not hasattr(r, "pubsub"):
            raise AttributeError("MockRedis does not support pubsub")

        # 使用 asyncio 在线程池中运行阻塞的 pubsub
        channel = batch_channel(batch_id)
        deadline = time.time() + timeout_sec

        def _subscribe_and_read():
            """在线程池中运行的阻塞订阅逻辑。"""
            pubsub = r.pubsub()
            pubsub.subscribe(channel)
            events = []
            try:
                while time.time() < deadline:
                    msg = pubsub.get_message(timeout=poll_interval)
                    if msg and msg["type"] == "message":
                        events.append(msg["data"])
                        # 收到 batch_done 或 completed 状态就停止
                        try:
                            data = json.loads(msg["data"])
                            if data.get("event") in ("batch_done",) or data.get("status") in ("completed", "partial_failed"):
                                break
                        except Exception:
                            pass
                    if events:
                        return events
                return events
            finally:
                pubsub.unsubscribe(channel)
                pubsub.close()

        # 用异步循环持续读取
        loop = asyncio.get_event_loop()
        deadline = time.time() + timeout_sec
        last_status = None

        while time.time() < deadline:
            # 非阻塞地检查是否有新消息（每次最多等 poll_interval 秒）
            events = await loop.run_in_executor(None, _subscribe_and_read)

            for raw in events:
                try:
                    data = json.loads(raw)
                    yield _sse_event(data.get("event", "progress"), data)
                    last_status = data.get("status")
                except Exception:
                    pass

            if last_status in ("completed", "partial_failed"):
                break

            await asyncio.sleep(0.1)

    except Exception as e:
        logger.debug(f"[Progress] Pub/Sub unavailable ({e}), falling back to DB polling")
        # 降级：轮询数据库
        async for event_str in _poll_db_progress(batch_id, timeout_sec):
            yield event_str

    # 最终推送一次完整快照确保前端状态同步
    final = await _get_batch_snapshot(batch_id)
    if final:
        yield _sse_event("batch_done", {**final, "event": "batch_done"})

    yield _sse_event("close", {"batch_id": batch_id, "message": "Stream closed"})


async def _poll_db_progress(
    batch_id: str,
    timeout_sec: int,
    interval: float = 2.0,
) -> AsyncGenerator[str, None]:
    """降级方案：轮询数据库获取进度。"""
    deadline = time.time() + timeout_sec
    last_completed = -1

    while time.time() < deadline:
        snapshot = await _get_batch_snapshot(batch_id)
        if not snapshot:
            await asyncio.sleep(interval)
            continue

        completed = snapshot.get("completed", 0)
        total = snapshot.get("total", 0)

        # 只在有变化时推送
        if completed != last_completed:
            last_completed = completed
            yield _sse_event("progress", snapshot)

        status = snapshot.get("status", "processing")
        if status in ("completed", "partial_failed"):
            break

        await asyncio.sleep(interval)


async def _get_batch_snapshot(batch_id: str) -> dict | None:
    """从数据库读取批次当前状态快照。"""
    try:
        from app.core.database import async_session_factory
        from app.models.observability import IngestionBatch, FileTrace, TraceStatus
        from sqlmodel import select, func

        async with async_session_factory() as session:
            batch = await session.get(IngestionBatch, batch_id)
            if not batch:
                return None

            # 统计各状态文件数
            stmt = (
                select(FileTrace.status, func.count(FileTrace.id).label("cnt"))
                .where(FileTrace.batch_id == batch_id)
                .group_by(FileTrace.status)
            )
            res = await session.execute(stmt)
            status_counts = {row.status: row.cnt for row in res}

            completed = status_counts.get(TraceStatus.SUCCESS, 0)
            failed = status_counts.get(TraceStatus.FAILED, 0) + status_counts.get(TraceStatus.PENDING_REVIEW, 0)
            total = batch.total_files
            percent = round(completed / max(total, 1) * 100, 1)

            if completed + failed >= total:
                status = "completed" if failed == 0 else "partial_failed"
            else:
                status = "processing"

            return {
                "event": "progress",
                "batch_id": batch_id,
                "total": total,
                "completed": completed,
                "failed": failed,
                "percent": percent,
                "status": status,
                "message": f"已完成 {completed}/{total} 个文件",
                "ts": time.time(),
            }
    except Exception as e:
        logger.warning(f"[Progress] DB snapshot failed: {e}")
        return None


def _sse_event(event_type: str, data: dict) -> str:
    """格式化为 SSE 协议格式。"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
