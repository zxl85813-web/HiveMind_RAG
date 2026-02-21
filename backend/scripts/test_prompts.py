"""
Prompt Engine 测试 — 验证四层组合是否正确生成 Prompt。
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from loguru import logger
from app.prompts.engine import prompt_engine


def main():
    logger.info("🧪 Prompt Engine 测试开始\n")

    # ============================================================
    #  1. 测试 Supervisor Routing Prompt
    # ============================================================
    logger.info("=" * 60)
    logger.info("📋 Test 1: Supervisor Routing Prompt")
    logger.info("=" * 60)

    supervisor_prompt = prompt_engine.build_supervisor_prompt(
        agents=[
            {"name": "rag_agent", "description": "知识检索与问答"},
            {"name": "code_agent", "description": "代码生成、执行与调试"},
            {"name": "web_agent", "description": "联网搜索实时信息"},
        ],
        memory_context="用户之前询问过 Python 异步编程相关问题。",
    )
    print(supervisor_prompt)
    print()

    # ============================================================
    #  2. 测试 Agent Task Prompt (with RAG context)
    # ============================================================
    logger.info("=" * 60)
    logger.info("📋 Test 2: RAG Agent Task Prompt")
    logger.info("=" * 60)

    agent_prompt = prompt_engine.build_agent_prompt(
        agent_name="rag_agent",
        task="查找关于 Python asyncio 的基础教程文档",
        rag_context=(
            "[Doc-001] asyncio 是 Python 3.4+ 引入的异步 I/O 框架...\n"
            "[Doc-002] 使用 async/await 语法可以编写并发代码..."
        ),
        memory_context="",
        tools_available=["vector_search", "keyword_search"],
    )
    print(agent_prompt)
    print()

    # ============================================================
    #  3. 测试 Reflection Prompt
    # ============================================================
    logger.info("=" * 60)
    logger.info("📋 Test 3: Reflection Prompt")
    logger.info("=" * 60)

    reflection_prompt = prompt_engine.build_reflection_prompt(
        user_query="如何用 Python 写一个异步 HTTP 服务器？",
        agent_name="code_agent",
        agent_response="你可以使用 aiohttp 库来创建异步 HTTP 服务器...",
        task_description="编写异步 HTTP 服务器示例代码",
    )
    print(reflection_prompt)
    print()

    # ============================================================
    #  4. 测试 Model Hint
    # ============================================================
    logger.info("=" * 60)
    logger.info("📋 Test 4: Model Hints")
    logger.info("=" * 60)

    for agent in ["supervisor", "rag_agent", "code_agent"]:
        hint = prompt_engine.get_model_hint(agent)
        logger.info(f"  {agent}: model_hint = {hint}")

    # ============================================================
    #  5. 测试 Available Agents
    # ============================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 Test 5: Available Agents (from YAML files)")
    logger.info("=" * 60)

    agents = prompt_engine.list_available_agents()
    logger.info(f"  Found {len(agents)} agents: {agents}")

    # ============================================================
    #  6. 对比: 旧的硬编码 vs 新的模板化
    # ============================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 对比: 旧硬编码 Prompt vs 新模板化 Prompt")
    logger.info("=" * 60)

    old_prompt = f"""You are the Supervisor of an intelligent agent swarm.
    Your goal is to route the user's request to the most appropriate agent.
    
    Available Agents:
    - rag_agent: 知识检索与问答
    - code_agent: 代码生成、执行与调试
    
    IMPORTANT: You MUST return a JSON object..."""

    logger.info(f"  旧 Prompt: {len(old_prompt)} chars, 硬编码在 swarm.py")
    logger.info(f"  新 Prompt: {len(supervisor_prompt)} chars, 从 YAML+Jinja2 生成")
    logger.info(f"  新 Prompt 包含: Base约束 + 角色定义 + 路由逻辑 + 记忆上下文 + 输出格式")

    logger.success("\n✅ 所有测试完成!")


if __name__ == "__main__":
    main()
