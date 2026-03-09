"""
Swarm Integration Test — 验证 PromptEngine + Artifact 集成。

测试内容:
    1. Swarm 使用 PromptEngine 生成 Prompt (不再硬编码)
    2. Reflection 用 LLM 做质量评估
    3. invoke() 支持 Pipeline context 注入
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))
load_dotenv(backend_dir / ".env")

from loguru import logger  # noqa: E402

from app.agents.swarm import AgentDefinition, SwarmOrchestrator  # noqa: E402
from app.core.config import settings  # noqa: E402


async def main():
    # Accept custom prompt from command line
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "用Python写一个斐波那契数列函数"

    logger.info("🚀 Swarm Test (PromptEngine integration)")
    logger.info(f"Config: Provider={settings.LLM_PROVIDER}, Model={settings.LLM_MODEL}")

    # 1. Create Swarm
    swarm = SwarmOrchestrator()

    # 2. Register Agents (model_hint auto-loaded from YAML)
    swarm.register_agent(
        AgentDefinition(
            name="rag_agent",
            description="Knowledge base retrieval and question answering",
        )
    )
    swarm.register_agent(
        AgentDefinition(
            name="code_agent",
            description="Code generation, execution, and debugging",
        )
    )

    # 3. Build graph
    await swarm.build_graph()

    # 4. Invoke
    logger.info(f"📤 User: {user_input}")
    final_state = await swarm.invoke(user_input)

    # 5. Display results
    messages = final_state.get("messages", [])
    logger.success(f"\n{'=' * 60}")
    logger.success(f"📊 Results ({len(messages)} messages)")
    logger.success(f"{'=' * 60}")

    for msg in messages:
        role = msg.type.upper()
        content = msg.content[:300] if msg.content else "(empty)"
        logger.success(f"[{role}]: {content}")

    logger.success(f"\nReflection count: {final_state.get('reflection_count', 0)}")
    logger.success(f"Final uncertainty: {final_state.get('uncertainty_level', 0):.2f}")


if __name__ == "__main__":
    asyncio.run(main())
