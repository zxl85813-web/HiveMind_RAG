
import asyncio
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.chat import User

async def fix_admin_role():
    async with async_session_factory() as session:
        # 1. Fix 'admin' user
        stmt = select(User).where(User.username == "admin")
        res = await session.execute(stmt)
        user = res.scalars().first()
        
        if user:
            print(f"Current role for 'admin': {user.role}")
            if user.role != "admin":
                user.role = "admin"
                session.add(user)
                await session.commit()
                print("Role updated to 'admin' for user 'admin'.")
            else:
                print("Role is already 'admin'.")
        else:
            print("User 'admin' not found.")

        # 2. Fix 'developer' user
        stmt = select(User).where(User.username == "developer")
        res = await session.execute(stmt)
        dev_user = res.scalars().first()
        
        if dev_user:
            print(f"Current role for 'developer': {dev_user.role}")
            if dev_user.role != "admin":
                dev_user.role = "admin"
                session.add(dev_user)
                await session.commit()
                print("Role updated to 'admin' for user 'developer'.")
            else:
                print("Role is already 'admin'.")
        else:
            print("User 'developer' not found.")

if __name__ == "__main__":
    asyncio.run(fix_admin_role())
