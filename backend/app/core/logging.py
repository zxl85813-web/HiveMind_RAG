"""
日志配置模块 — 使用 loguru 统一所有日志输出。

项目中所有日志必须通过本模块的 logger 实例:
    from app.core.logging import logger

禁止使用:
    - print()
    - logging.getLogger()
    - 直接 from loguru import logger (应统一从此处 import)

参见: .agent/rules/coding-standards.md
参见: REGISTRY.md > 后端 > 核心配置 > logging
"""

import sys
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

from app.core.config import settings

# 🛰️ 链路追踪上下文变量 (Cross-Request Trace ID)
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="system-internal")

def get_trace_logger(module: str):
    """
    统一日志辅助器：注入 TraceContext 并符合 Frontend TS 定义的 UnifiedLog 契约。
    """
    return logger.bind(
        module=module,
        platform="BE",
        env=settings.ENV,
        trace_id=trace_id_var.get()
    )

# 移除默认 handler
logger.remove()

# === Console Handler (开发环境) ===
logger.add(
    sys.stderr,
    level="DEBUG",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# === File Handler (结构化日志) ===
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    LOG_DIR / "hivemind_{time:YYYY-MM-DD}.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="00:00",  # 每天轮转
    retention="30 days",  # 保留 30 天
    compression="gz",  # 压缩旧日志
    encoding="utf-8",
    serialize=True,  # 开启 JSON 格式输出，方便与前端日志对齐与自动化分析
)

# === Error-only Handler ===
logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="00:00",
    retention="90 days",
    compression="gz",
    encoding="utf-8",
    serialize=True,
)


def setup_logging(debug: bool = True) -> None:
    """
    根据运行环境调整日志配置。

    在 main.py 的 lifespan 中调用:
        setup_logging(settings.DEBUG)
    """
    if not debug:
        # 生产环境: 调高 Console 级别，减少噪音
        logger.remove()
        logger.add(sys.stderr, level="WARNING", colorize=False)
        logger.add(
            LOG_DIR / "hivemind_{time:YYYY-MM-DD}.log",
            level="INFO",
            rotation="00:00",
            retention="30 days",
            compression="gz",
        )
        logger.add(
            LOG_DIR / "error_{time:YYYY-MM-DD}.log",
            level="ERROR",
            rotation="00:00",
            retention="90 days",
            compression="gz",
        )

    logger.info("Logging initialized (debug={})", debug)


def setup_script_context(script_name: str) -> None:
    """
    为独立运行的脚本 (backend/scripts/*.py) 初始化可观测性上下文。
    
    1. 自动从 GITHUB_RUN_ID 或环境变量注入 trace_id。
    2. 设置 UnifiedLog 契约所需的模块名称。
    """
    import os
    import uuid

    # 🛰️ 优先从环境变量获取由 CI 注入的 ID，或者本地随机
    raw_id = os.getenv("GITHUB_RUN_ID") or os.getenv("TRACE_ID")
    if not raw_id:
        raw_id = f"local-{str(uuid.uuid4())[:8]}"

    trace_id_var.set(raw_id)

    logger.info(
         "Script context initialized: module={module}, trace_id={trace_id}",
         module=f"scripts.{script_name}",
         trace_id=raw_id
    )


# 导出统一的 logger 实例与工具函数
__all__ = ["get_trace_logger", "logger", "setup_logging", "setup_script_context", "trace_id_var"]
