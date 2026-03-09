import asyncio
import os
import sys

# Ensure backend directory is in path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger

from app.agents.swarm import AgentDefinition, SwarmOrchestrator


async def run():
    logger.info("🤖 Booting Swarm Orchestrator and waking up QA Tester Agent...")

    # 1. Provide the absolute path to the design document
    doc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/design/multi_tier_memory.md"))

    with open(doc_path, encoding="utf-8") as f:
        doc_content = f.read()

    # 2. Init Swarm and Register the QA Agent
    swarm = SwarmOrchestrator()
    qa_agent = AgentDefinition(
        name="qa_tester",
        description=(
            "Expert QA Test Engineer. Used exclusively to generate pytest scaffolding from markdown design docs."
        ),
        model_hint="balanced",  # Use default model for now
    )
    swarm.register_agent(qa_agent)

    # 3. Instruct the QA Agent
    user_prompt = f"""
    Please generate a complete, runnable `pytest` file to test the following design document.
    Follow all constraints of your DDT (Design-Driven Testing) philosophy.
    Include mocks since we cannot connect to real Elasticsearch or Neo4j in Unit Tests.

    [DOCUMENT START]
    {doc_content}
    [DOCUMENT END]

    Return ONLY the raw Python code.
    """

    logger.info("⏳ Sending Design Document to QA Agent (this may take ~10 seconds)...")

    # 4. Invoke the Swarm
    result = await swarm.invoke(user_message=user_prompt)

    # 5. Extract output
    messages = result.get("messages", [])
    output = messages[-1].content if messages else "No response"

    # 6. Save output
    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "qa_generated_test.py"))
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(output)

    logger.info(f"✅ Auto-Generated Test saved to: {out_file}")
    print("\n--- SNIPPET OF AGENT'S WORK ---")
    lines = output.split("\n")
    print("\n".join(lines[:20]))
    print("... (see file for FULL code) ...")


if __name__ == "__main__":
    asyncio.run(run())
