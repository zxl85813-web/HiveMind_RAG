import asyncio
import json
from app.core.database import async_session_factory
from app.services.observability_service import get_ai_diagnostics

async def main():
    try:
        async with async_session_factory() as session:
            result = await get_ai_diagnostics(session)
            print("--- AI ARCHITECTURE DIAGNOSIS REPORT ---")
            print(f"Status: {result['status']}")
            print("\nAnalysis Content:")
            print(result['analysis'])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
