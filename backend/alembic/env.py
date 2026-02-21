import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from sqlmodel import SQLModel

# 导入所有 Model 以便 Alembic 正确识别 Schema 变更
from app.models.user import User
from app.models.chat import Conversation, Message
from app.models.knowledge import KnowledgeBase, Document
from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 注入 SQLModel 的 Metadata
target_metadata = SQLModel.metadata

# 从 Settings 获取数据库连接串 (覆盖 alembic.ini 的硬编码)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """运行离线迁移 (生成 SQL 文件)。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        # 这里实际上还没有进行修改，只有 migrate 命令会真正提交
        context.run_migrations()


async def run_migrations_online() -> None:
    """运行在线迁移 (连接数据库)。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
