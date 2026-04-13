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
        # 1. 确保基础用户存在 (仅在 DEBUG 模式下)
        if settings.DEBUG:
            from app.auth.security import hash_password
            
            users_to_seed = [
                {
                    "id": "mock-user-001",
                    "username": "developer",
                    "email": "dev@hivemind.local",
                    "password": "password",
                    "role": "admin"
                },
                {
                    "id": "admin-user",
                    "username": "admin",
                    "email": "admin@hivemind.local",
                    "password": "admin123",
                    "role": "admin"
                }
            ]
            
            from sqlalchemy import select
            
            for u_data in users_to_seed:
                # Check by username instead of ID to avoid duplicate constraint violations
                stmt = select(User).where(User.username == u_data["username"])
                res = await session.execute(stmt)
                user = res.scalars().first()
                
                if not user:
                    logger.info(f"Seeding user: {u_data['username']}")
                    new_user = User(
                        id=u_data["id"],
                        username=u_data["username"],
                        email=u_data["email"],
                        hashed_password=hash_password(u_data["password"]),
                        role=u_data["role"],
                    )
                    session.add(new_user)
                else:
                    # 🛰️ [Harden]: Ensure role is correct even if user exists
                    if user.role != u_data["role"]:
                        logger.warning(f"Reconciling role for {u_data['username']}: {user.role} -> {u_data['role']}")
                        user.role = u_data["role"]
                        session.add(user)
                    logger.debug(f"User {u_data['username']} already exists.")
            
            await session.commit()

        # 2. 确保 Swarm 初始数据存在 (仅在 DEBUG 模式下)
        if settings.DEBUG:
            from sqlalchemy import select

            from app.models.agents import (
                ReflectionEntry,
                ReflectionSignalType,
                ReflectionType,
                TodoItem,
                TodoPriority,
                TodoStatus,
            )

            # TODO Seeding
            existing_todos = await session.execute(select(TodoItem).limit(1))
            if not existing_todos.scalar():
                logger.info("Seeding initial swarm TODOs...")
                session.add_all(
                    [
                        TodoItem(
                            title="分布式 Agent 编排实现",
                            description="将 Supervisor 模式扩展为支持多 Agent 协同。计划由 Core Agent 领头实现。",
                            priority=TodoPriority.HIGH,
                            status=TodoStatus.IN_PROGRESS,
                            created_by="Supervisor",
                            assigned_to="Core Agent",
                        ),
                        TodoItem(
                            title="优化向量记忆检索阈值",
                            description="针对 RAG Agent 的召回率进行微调，提高回答的准确性。",
                            priority=TodoPriority.MEDIUM,
                            status=TodoStatus.PENDING,
                            created_by="RAG Agent",
                            assigned_to="System",
                        ),
                    ]
                )
                await session.commit()

            # Reflection Seeding
            existing_reflections = await session.execute(select(ReflectionEntry).limit(1))
            if not existing_reflections.scalar():
                logger.info("Seeding initial swarm reflections...")
                session.add_all(
                    [
                        ReflectionEntry(
                            type=ReflectionType.SELF_EVAL,
                            signal_type=ReflectionSignalType.INSIGHT,
                            agent_name="Supervisor",
                            topic="task-routing",
                            match_key="routing",
                            tags=["orchestration", "quality"],
                            summary="检测到多步查询意图，已自动分发子任务。",
                            confidence_score=0.95,
                            action_taken="Spawned RAG & Web Agents",
                        ),
                        ReflectionEntry(
                            type=ReflectionType.KNOWLEDGE_GAP,
                            signal_type=ReflectionSignalType.GAP,
                            agent_name="RAG Agent",
                            topic="roadmap-knowledge",
                            match_key="roadmap",
                            tags=["knowledge-gap"],
                            summary="未找到关于 '2025 项目路线图' 的内部文档。",
                            confidence_score=0.45,
                            action_taken="委派 Web Agent 搜索外部上下文",
                        ),
                    ]
                )
                await session.commit()
