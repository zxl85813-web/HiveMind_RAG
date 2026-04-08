import asyncio
import sys
import os

# Adjust path to find app
sys.path.append(os.getcwd() + "/backend")

from app.services.rag_gateway import RAGGateway

async def main():
    gateway = RAGGateway()
    print("Testing Unified RAG Gateway Refinement...")
    
    # Test 1: Standard retrieval
    print("\n--- Test 1: Standard Retrieval ---")
    res = await gateway.retrieve(query="什么是 HiveMind?", kb_ids=["default"])
    print(f"Latency: {res.processing_time_ms:.2f}ms")
    print(f"Results: {len(res.fragments)}")
    
    # Test 2: Development retrieval with Graph Fusion
    print("\n--- Test 2: Dev Retrieval + Graph Fusion ---")
    res_dev = await gateway.retrieve_for_development(query="How does the Swarm relate to GraphStore?", kb_ids=["default"], include_graph=True)
    print(f"Latency: {res_dev.processing_time_ms:.2f}ms")
    print(f"Strategy: {res_dev.retrieval_strategy}")
    for i, f in enumerate(res_dev.fragments[:3]):
        print(f"[{i}] {f.content[:100]}... (Source: {f.metadata.get('source')})")

    # Test 3: Radar Trigger
    print("\n--- Test 3: Telemetry Radar Trigger ---")
    res_radar = await gateway.retrieve(query="Show me the latest system errors", kb_ids=["default"])
    found_radar = any(f.metadata.get("source") == "telemetry_radar" for f in res_radar.fragments)
    print(f"Radar Hit: {found_radar}")

if __name__ == "__main__":
    asyncio.run(main())
