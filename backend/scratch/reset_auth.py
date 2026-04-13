import asyncio
from sqlmodel import select
from app.core.database import async_session_factory
from app.models.chat import User
from app.auth.security import hash_password

async def reset_passwords():
    async with async_session_factory() as session:
        # Reset admin
        admin_stmt = select(User).where(User.username == 'admin')
        admin = (await session.execute(admin_stmt)).scalars().first()
        if admin:
            print(f"Updating password for admin (Current hash: {admin.hashed_password[:10]}...)")
            admin.hashed_password = hash_password("admin123")
            session.add(admin)
        
        # Reset developer
        dev_stmt = select(User).where(User.username == 'developer')
        dev = (await session.execute(dev_stmt)).scalars().first()
        if dev:
            print(f"Updating password for developer (Current hash: {dev.hashed_password[:10]}...)")
            dev.hashed_password = hash_password("password")
            session.add(dev)
            
        await session.commit()
        print("Done! admin -> admin123, developer -> password")

if __name__ == "__main__":
    asyncio.run(reset_passwords())
