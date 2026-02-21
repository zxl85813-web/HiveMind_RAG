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
from pathlib import Path

from loguru import logger

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
    serialize=False,  # 设为 True 可输出 JSON 格式
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


# 导出统一的 logger 实例
__all__ = ["logger", "setup_logging"]
