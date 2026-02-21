"""
脚本：创建系统超级管理员。
用法：python -m backend.scripts.create_superuser --username admin --password "123456"

注意：必须在 backend/ 根目录下运行 (因为 module import 路径问题)。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 将 backend/ 目录加入 sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.core.database import get_db_session, init_db
from app.auth.security import hash_password
from app.models.user import User


async def create_superuser(username: str, password: str, email: str = "admin@example.com"):
    """创建超级管理员。"""
    print(f"🔄 Creating superuser: {username} ({email})...")
    
    # 确保数据库已初始化 (开发环境)
    await init_db()

    async for session in get_db_session():
        # TODO: 检查是否存在
        # existing = await session.exec(select(User).where(User.username == username)).first()
        # if existing: print("🚫 User already exists"); return

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            role="admin",  # 超级管理员角色
        )
        session.add(user)
        await session.commit()
        print(f"✅ Superuser created successfully! ID: {user.id}")
        break


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_superuser.py <username> <password> [email]")
        sys.exit(1)
        
    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else "admin@example.com"

    asyncio.run(create_superuser(username, password, email))
