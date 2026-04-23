import asyncio
from sqlmodel import select
from app.core.database import async_session_factory
from app.models.chat import User
from app.auth.security import hash_password

async def seed_admin():
    async with async_session_factory() as session:
        statement = select(User).where(User.username == "admin")
        result = await session.exec(statement)
        user = result.first()
        
        if not user:
            print("Creating admin user...")
            admin = User(
                username="admin",
                hashed_password=hash_password("admin123"),
                full_name="Administrator",
                role="admin",
                is_active=True
            )
            session.add(admin)
            await session.commit()
            print("Admin user created successfully.")
        else:
            print("Admin user exists, resetting password...")
            user.hashed_password = hash_password("admin123")
            session.add(user)
            await session.commit()
            print("Admin password reset successfully.")

if __name__ == "__main__":
    asyncio.run(seed_admin())
