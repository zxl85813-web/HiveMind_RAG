import asyncio
from app.services.memory.episodic_service import episodic_memory_service
from app.models.episodic import EpisodicMemory

async def check():
    print("Checking Episodic Memory Service...")
    # Check if we can instantiate or access
    print(f"Service instance: {episodic_memory_service}")
    print(f"Model table name: {EpisodicMemory.__tablename__}")

if __name__ == "__main__":
    asyncio.run(check())
