"""
统一异常处理模块。

定义业务异常类和 FastAPI 全局异常处理器。
所有 API 错误响应格式统一为:
    {
        "error_code": "NOT_FOUND",
        "message": "Resource not found",
        "detail": { ... }   # 可选
    }

参见: REGISTRY.md > 后端 > 核心配置 > exceptions
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import logger

# ==========================================
#  业务异常类
# ==========================================


class AppError(Exception):
    """应用基础异常 — 所有业务异常的父类。"""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: dict[str, Any] | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(AppError):
    """资源不存在。"""

    def __init__(self, resource: str, resource_id: str | None = None):
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(
            error_code="NOT_FOUND",
            message=msg,
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"resource": resource, "id": resource_id},
        )


class ValidationError(AppError):
    """数据校验失败。"""

    def __init__(self, message: str, detail: dict[str, Any] | None = None):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class AuthenticationError(AppError):
    """认证失败。"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            error_code="AUTHENTICATION_ERROR",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class PermissionError(AppError):
    """权限不足。"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            error_code="PERMISSION_DENIED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConflictError(AppError):
    """资源冲突。"""

    def __init__(self, message: str, detail: dict[str, Any] | None = None):
        super().__init__(
            error_code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class ExternalServiceError(AppError):
    """外部服务调用失败 (LLM / MCP / 第三方 API)。"""

    def __init__(self, service: str, message: str, detail: dict[str, Any] | None = None):
        super().__init__(
            error_code="EXTERNAL_SERVICE_ERROR",
            message=f"[{service}] {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"service": service, **(detail or {})},
        )


class BudgetExceededError(AppError):
    """Tenant has consumed its daily token budget — circuit-breaker tripped."""

    def __init__(self, tenant_id: str, used: int, limit: int):
        super().__init__(
            error_code="BUDGET_EXCEEDED",
            message=(
                f"Tenant '{tenant_id}' exceeded its daily token budget "
                f"({used:,} / {limit:,} tokens). Try again tomorrow or upgrade your plan."
            ),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"tenant_id": tenant_id, "used": used, "limit": limit},
        )


# ==========================================
#  全局异常处理器注册
# ==========================================


def register_exception_handlers(app: FastAPI) -> None:
    """
    在 main.py 中调用以注册全局异常处理器:
        register_exception_handlers(app)
    """

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        """处理所有自定义业务异常。"""
        logger.warning(
            "AppError: {} | {} | detail={}",
            exc.error_code,
            exc.message,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    # Rate limiter raises a non-AppError exception so we wrap it explicitly.
    try:
        from app.services.governance.rate_limiter import RateLimitExceeded

        @app.exception_handler(RateLimitExceeded)
        async def rate_limit_handler(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
            logger.warning(
                "RateLimitExceeded: scope={} key={} {}/{}/{}s",
                exc.scope, exc.key, exc.observed, exc.limit, exc.window_sec,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error_code": "RATE_LIMITED",
                    "message": (
                        f"Rate limit exceeded ({exc.observed}/{exc.limit} per "
                        f"{exc.window_sec}s). Slow down."
                    ),
                    "detail": {
                        "scope": exc.scope,
                        "limit": exc.limit,
                        "window_sec": exc.window_sec,
                        "observed": exc.observed,
                    },
                },
                headers={"Retry-After": str(max(1, exc.window_sec))},
            )
    except Exception:  # noqa: BLE001
        # rate_limiter module not importable in minimal envs — skip silently
        pass

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        """兜底: 处理所有未捕获异常。"""
        logger.exception("Unhandled exception: {}", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "detail": {},
            },
        )
