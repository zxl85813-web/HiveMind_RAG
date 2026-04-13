import asyncio
from sqlmodel import select
from app.core.database import async_session_factory
from app.models.chat import User
from app.auth.security import verify_password

async def test_login():
    async with async_session_factory() as session:
        username = "admin"
        import os
        password = os.getenv("TEST_ADMIN_PASSWORD", "placeholder_for_security")
        
        stmt = select(User).where(User.username == username)
        res = await session.execute(stmt)
        user = res.scalars().first()
        
        if not user:
            print(f"User '{username}' NOT FOUND in DB.")
            return

        print(f"User found: {user.username}")
        print(f"Stored Hash: {user.hashed_password}")
        
        is_correct = verify_password(password, user.hashed_password)
        print(f"Password '{password}' verify result: {is_correct}")

if __name__ == "__main__":
    asyncio.run(test_login())
