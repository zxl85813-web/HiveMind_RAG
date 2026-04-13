import asyncio
from sqlmodel import select
from app.core.database import async_session_factory
from app.models.chat import User

async def check_users():
    async with async_session_factory() as session:
        statement = select(User)
        result = await session.execute(statement)
        users = result.scalars().all()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f"- {u.username} (ID: {u.id}, Role: {u.role})")

if __name__ == "__main__":
    asyncio.run(check_users())
