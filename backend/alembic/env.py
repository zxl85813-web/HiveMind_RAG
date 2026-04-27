import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models import *  # noqa: F403

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 注入 SQLModel 的 Metadata
target_metadata = SQLModel.metadata

# 注意: 不使用 config.set_main_option("sqlalchemy.url", ...)
# 因为 ConfigParser 会将密码中的 % 视为插值语法导致报错。
# 改为在 run_migrations_online 中直接使用 settings.DATABASE_URL 建立引擎。


def run_migrations_offline() -> None:
    """运行离线迁移 (生成 SQL 文件)。"""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """运行在线迁移 (连接数据库)。"""
    # 直接用 settings.DATABASE_URL 创建引擎, 绕过 ConfigParser 对 % 的解析
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
