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
        # 1. 确保 Admin 用户存在 (无论是否在 DEBUG 模式下，供登录测试使用)
        from sqlalchemy import select
        stmt = select(User).where(User.username == "admin")
        res = await session.execute(stmt)
        admin_user = res.scalar_one_or_none()
        if not admin_user:
            logger.info("Seeding base admin user...")
            from app.auth.security import hash_password
            base_admin = User(
                id="admin-user-001",
                username="admin",
                email="admin@hivemind.local",
                hashed_password=hash_password("admin123"),
                role="admin",
            )
            session.add(base_admin)
            await session.commit()
            logger.info("Base admin user seeded successfully: username='admin', password='admin123'")
        else:
            logger.info("Base admin user already exists.")

        # 2. 确保 Swarm 初始数据存在 (仅在 DEBUG 模式下)
        if settings.DEBUG:
            from app.models.agents import TodoItem, ReflectionEntry, TodoPriority, TodoStatus, ReflectionType
            from sqlalchemy import select

            # TODO Seeding
            existing_todos = await session.execute(select(TodoItem).limit(1))
            if not existing_todos.scalar():
                logger.info("Seeding initial swarm TODOs...")
                session.add_all([
                    TodoItem(
                        title="分布式 Agent 编排实现",
                        description="将 Supervisor 模式扩展为支持多 Agent 协同。计划由 Core Agent 领头实现。",
                        priority=TodoPriority.HIGH,
                        status=TodoStatus.IN_PROGRESS,
                        created_by="Supervisor",
                        assigned_to="Core Agent"
                    ),
                    TodoItem(
                        title="优化向量记忆检索阈值",
                        description="针对 RAG Agent 的召回率进行微调，提高回答的准确性。",
                        priority=TodoPriority.MEDIUM,
                        status=TodoStatus.PENDING,
                        created_by="RAG Agent",
                        assigned_to="System"
                    )
                ])
                await session.commit()

            # Reflection Seeding
            existing_reflections = await session.execute(select(ReflectionEntry).limit(1))
            if not existing_reflections.scalar():
                logger.info("Seeding initial swarm reflections...")
                session.add_all([
                    ReflectionEntry(
                        type=ReflectionType.SELF_EVAL,
                        agent_name="Supervisor",
                        summary="检测到多步查询意图，已自动分发子任务。",
                        confidence_score=0.95,
                        action_taken="Spawned RAG & Web Agents"
                    ),
                    ReflectionEntry(
                        type=ReflectionType.KNOWLEDGE_GAP,
                        agent_name="RAG Agent",
                        summary="未找到关于 '2025 项目路线图' 的内部文档。",
                        confidence_score=0.45,
                        action_taken="委派 Web Agent 搜索外部上下文"
                    )
                ])
                await session.commit()
