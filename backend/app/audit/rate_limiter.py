"""
API 限流 — per-user / per-IP 请求限制。

策略:
    - 固定窗口 (Fixed Window): 每分钟/每小时请求上限
    - 滑动窗口 (Sliding Window): 更平滑的限流
    - Token Bucket: 突发流量容忍

存储:
    - 开发: 内存 dict
    - 生产: Redis (TTL)

参见: REGISTRY.md > 后端 > audit > rate_limiter
"""

from datetime import UTC, datetime

from loguru import logger


class RateLimitError(Exception):
    """请求超出限流。"""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s")


class RateLimiter:
    """
    内存版限流器 (开发/单实例)。

    生产环境应替换为 Redis 实现。

    用法:
        limiter = RateLimiter(max_requests=60, window_seconds=60)

        # 在 FastAPI 依赖中使用:
        async def rate_limit_dep(request: Request):
            key = request.client.host
            limiter.check(key)
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, list[float]] = {}  # key → [timestamps]

    def check(self, key: str) -> bool:
        """
        检查是否超限。

        Args:
            key: 限流键 (user_id 或 IP)

        Returns:
            True 如果允许, 否则抛出 RateLimitError

        Raises:
            RateLimitError: 超出限流
        """
        now = datetime.now(UTC).timestamp()
        window_start = now - self.window_seconds

        # 清理过期记录
        if key in self._store:
            self._store[key] = [t for t in self._store[key] if t > window_start]
        else:
            self._store[key] = []

        if len(self._store[key]) >= self.max_requests:
            oldest = self._store[key][0]
            retry_after = int(oldest + self.window_seconds - now) + 1
            logger.warning("🚫 Rate limit exceeded for key={}", key)
            raise RateLimitError(retry_after=retry_after)

        self._store[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        """获取剩余配额。"""
        now = datetime.now(UTC).timestamp()
        window_start = now - self.window_seconds

        timestamps = self._store.get(key, [])
        active = [t for t in timestamps if t > window_start]
        return max(0, self.max_requests - len(active))


# === 预设限流器实例 ===

# 通用 API: 60 req/min
api_limiter = RateLimiter(max_requests=60, window_seconds=60)

# Chat (LLM 调用, 更严格): 20 req/min
chat_limiter = RateLimiter(max_requests=20, window_seconds=60)

# 文件上传: 10 req/min
upload_limiter = RateLimiter(max_requests=10, window_seconds=60)
