"""
脚本：创建系统超级管理员。
用法：python -m backend.scripts.create_superuser --username admin --password "<your_password>"

注意：必须在 backend/ 根目录下运行 (因为 module import 路径问题)。
"""

# ruff: noqa: E402

import sys
import asyncio
from pathlib import Path

# 1. 路径注入与环境初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(backend_dir.parent) not in sys.path:
    sys.path.insert(0, str(backend_dir.parent))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("create_superuser")
t_logger = get_trace_logger("scripts.create_superuser")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

from app.auth.security import hash_password
from app.core.database import get_db_session, init_db
from app.models.chat import User


async def create_superuser(username: str, password: str, email: str = "admin@example.com"):
    """创建超级管理员。"""
    t_logger.info(f"🔄 Creating superuser: {username} ({email})...", action="user_creating")

    # 确保数据库已初始化 (开发环境)
    await init_db()

    async for session in get_db_session():
        # Check if already exists
        from sqlmodel import select
        stmt = select(User).where(User.username == username)
        res = await session.execute(stmt)
        existing = res.scalars().first()
        if existing:
             t_logger.warning("🚫 User already exists", action="user_exists")
             return

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            role="admin",  # 超级管理员角色
        )
        session.add(user)
        await session.commit()
        t_logger.success(f"✅ Superuser created successfully! ID: {user.id}", action="user_created", meta={"id": str(user.id)})
        break


if __name__ == "__main__":
    if len(sys.argv) < 3:
        t_logger.error("Usage: python create_superuser.py <username> <password> [email]", action="usage_error")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else "admin@example.com"

    asyncio.run(create_superuser(username, password, email))
