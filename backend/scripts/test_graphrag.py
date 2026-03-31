import asyncio
import os
import sys

# Add backend directory to sys path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.rag_gateway import RAGGateway

async def test_hybrid_graphrag():
    print("🚀 Testing Hybrid GraphRAG Query\n" + "-"*50)
    
    gateway = RAGGateway()
    
    # We will simulate a query about our routing components or knowledge base
    # NOTE: Since we don't have active vector KBs in this ad-hoc test, 
    # the kb_ids=[] will skip the actual vector part, but we will test the graph lookup by query
    # The Cypher matches by id, name or path.
    # We will search for 'knowledge' hoping to hit knowledge.py or knowledge.tsx or KnowledgeBase model
    query = "knowledge"
    print(f"Query: '{query}'")
    
    # We simulate an empty kb_ids list, so vector_sources will be empty initially.
    # The cypher should still match nodes containing the query text and expand them!
    
    response = await gateway.retrieve_for_development(
        query=query,
        kb_ids=[],
        top_k=5,
        include_graph=True
    )
    
    print("\n✅ Response Strategy:", response.retrieval_strategy)
    print("✅ Total Found:", response.total_found)
    print("\nFragments Returned:")
    for frag in response.fragments:
        print(f" [Score: {frag.score}] {frag.content}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_graphrag())
