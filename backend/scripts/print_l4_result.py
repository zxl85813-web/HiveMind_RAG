
import asyncio
import sys
from pathlib import Path

# Setup Path
backend_dir = Path(r"c:\Users\linkage\Desktop\aiproject\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.agents.memory_bridge import SwarmMemoryBridge

async def run():
    bridge = SwarmMemoryBridge(user_id="l4_test_user")
    context = await bridge.load_historical_context("security_guide.py audit")
    print("--- L4 EVOLUTIONARY CONTEXT RECALL ---")
    # Safe print: Strip non-ASCII for Windows console
    safe_context = context.encode('ascii', 'ignore').decode('ascii')
    print(safe_context)
    print("--------------------------------------")

if __name__ == "__main__":
    asyncio.run(run())
