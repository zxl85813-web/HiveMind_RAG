
import asyncio
from sqlmodel import select
from app.core.database import async_session_factory
from app.models.chat import User
from app.core.security import hash_password

async def seed_admin():
    async with async_session_factory() as session:
        # Check if admin exists
        statement = select(User).where(User.username == "admin")
        results = await session.execute(statement)
        user = results.scalars().first()
        
        if not user:
            print("Creating default admin user...")
            admin_user = User(
                username="admin",
                email="admin@hivemind.ai",
                hashed_password=hash_password("admin123"),
                is_active=True,
                is_superuser=True
            )
            session.add(admin_user)
            await session.commit()
            print("Admin user 'admin' created with password 'admin123'")
        else:
            print("Admin user already exists.")

if __name__ == "__main__":
    asyncio.run(seed_admin())
