from typing import Any
from redis import Redis
from app.core.config import settings
from app.core.logging import get_trace_logger, trace_id_var

logger = get_trace_logger("core.redis")

class MockRedis:
    """
    开发环境备灾 Mock (TASK-GOV-001)。
    当本地未安装物理 Redis 时，自动接管流量，防止系统崩溃。
    """
    def __init__(self, *args, **kwargs):
        self._storage = {}
        logger.warning("⚠️ [Redis] No physical Redis found. Using IN-MEMORY MOCK.")

    def execute_command(self, *args, **options):
        # Implementation of basic dict-based mock if needed
        return None
    
    def ping(self): return True
    def rpop(self, key): return None
    def rpush(self, key, val): return 1
    def get(self, key): return self._storage.get(key)
    def set(self, key, val, **kwargs): self._storage[key] = val; return True

class TraceableRedis(Redis):
    """
    带链路追踪感的 Redis 客户端包装器 (TASK-GOV-001)。
    """
    def execute_command(self, *args, **options):
        trace_id = trace_id_var.get()
        command = args[0] if args else "UNKNOWN"
        try:
            return super().execute_command(*args, **options)
        except Exception as e:
            logger.error(f"❌ [Redis] {command} failed for trace={trace_id}: {e}")
            raise

def get_redis_client() -> Any:
    """
    获取 Redis 客户端，带自动降级保护。
    [Fix-04] 超时从 1s 调整为 3s，防止网络抖动触发误降级。
    """
    if not settings.REDIS_URL:
        return MockRedis()

    last_exc: Exception | None = None
    for attempt in range(2):  # 最多重试 1 次
        try:
            client = TraceableRedis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3,   # 从 1s 调整为 3s
                socket_timeout=3,
                retry_on_timeout=True,
            )
            client.ping()
            return client
        except Exception as e:
            last_exc = e
            logger.warning(f"⚠️ [Redis] Connection attempt {attempt + 1} failed: {e}")

    logger.error(f"❌ [Redis] All connection attempts failed, falling back to MockRedis. Last error: {last_exc}")
    return MockRedis()
