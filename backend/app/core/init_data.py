import logging

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.chat import User

logger = logging.getLogger(__name__)


async def init_base_data() -> None:
    """
    初始化系统的基础数据 (Seeding)。
    用于确保开发环境和生产环境有必要的初始状态。
    """
    logger.info("Checking database seeding status...")

    async with async_session_factory() as session:
        # 1. 确保 Mock 用户存在 (仅在 DEBUG 模式下)
        if settings.DEBUG:
            mock_user_id = "mock-user-001"
            user = await session.get(User, mock_user_id)
            if not user:
                logger.info(f"Seeding mock user: {mock_user_id}")
                # 开发环境 mock 用户 — 使用预计算的 bcrypt hash (原文: dev123456)
                mock_user = User(
                    id=mock_user_id,
                    username="developer",
                    email="dev@hivemind.local",
                    hashed_password="$2b$12$LJ3m4ys3Lk0kXx0z0z0z0OeZ5V5V5V5V5V5V5V5V5V5V5V5V5u",  # noqa: S105
                    role="admin",
                )
                session.add(mock_user)
                await session.commit()
            else:
                logger.debug(f"Mock user {mock_user_id} already exists.")

        # 可以在此处添加其他初始化数据
        # 例如: 默认的 System Prompt 模板、基础配置项等
