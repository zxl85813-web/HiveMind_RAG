"""
数据库连接与会话管理模块。

提供:
    - AsyncEngine 创建与配置
    - AsyncSession 工厂
    - get_db_session 依赖注入函数
    - 数据库初始化/关闭生命周期管理

参见: REGISTRY.md > 后端 > 核心配置 > database
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.logging import logger

# === Engine 配置 ===

# 根据数据库类型调整配置
db_config = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

if "sqlite" in settings.DATABASE_URL:
    # SQLite 特有配置
    db_config["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL/MySQL 等连接池配置
    db_config["pool_size"] = 10
    db_config["max_overflow"] = 20
    db_config["pool_recycle"] = 3600

engine = create_async_engine(settings.DATABASE_URL, **db_config)

# === Session 工厂 ===
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """
    初始化数据库 — 在 app lifespan startup 中调用。

    开发环境: 自动创建表 (生产环境请用 Alembic 迁移)。
    """
    logger.info("Initializing database connection...")

    # SQLite 需要在 engine.begin() 前确保目录存在
    # (但在 docker/local dev 中通常由挂载解决，或 sqlmodel 自动处理)

    async with engine.begin():
        if settings.DEBUG:
            # 开发环境不再自动同步表结构，全面启用 Alembic
            # await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Database initialized (metadata sync disabled, use Alembic instead)")
        else:
            logger.info("Database connected (production — use Alembic for migrations)")


async def close_db() -> None:
    """关闭数据库连接 — 在 app lifespan shutdown 中调用。"""
    logger.info("Closing database connection...")
    await engine.dispose()
    logger.info("Database connection closed")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入 — 获取数据库 Session。

    用法:
        @router.get("/")
        async def handler(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
