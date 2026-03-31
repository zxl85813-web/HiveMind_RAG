import asyncio
import os
import sys

# Add backend directory to sys path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.memory.tier.graph_index import graph_index

async def test_agent_memory():
    print("🧠 Testing Agent Style Memory Extraction & Retrieval\n" + "-"*50)
    
    agent_name = "ReactFrontendCoder"
    user_feedback = "I noticed you didn't add comments. From now on, all TypeScript components MUST have detailed JSDoc comments explaining the props and return values. Also, strictly use camelCase for variables."
    
    print(f"User Feedback: '{user_feedback}'\n")
    print(f"... Extracting via LLM and storing to Neo4j for agent '{agent_name}' ...")
    
    await graph_index.record_agent_preference(agent_name, user_feedback)
    
    print("\n... Retrieving stored preferences from Neo4j ...")
    preferences = await graph_index.get_agent_preferences(agent_name)
    
    if preferences:
        print("\n✅ Found injected preferences for System Prompt:")
        for pref in preferences:
            print(f"  {pref}")
    else:
        print("\n❌ No preferences retrieved. Check Neo4j connection.")

if __name__ == "__main__":
    asyncio.run(test_agent_memory())
