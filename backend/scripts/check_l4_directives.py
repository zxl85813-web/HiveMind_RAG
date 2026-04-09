
import asyncio
from app.core.database import async_session_factory
from app.models.agents import ReflectionEntry
from sqlmodel import select

async def check():
    async with async_session_factory() as s:
        res = await s.exec(select(ReflectionEntry))
        items = res.all()
        print(f"Total Reflections: {len(items)}")
        for i in items:
            directive = i.details.get("analysis", {}).get("cognitive_directive")
            if directive:
                print(f"Topic: {i.topic} | Directive: {directive}")

if __name__ == "__main__":
    asyncio.run(check())
