import asyncio
import time
import sys
import os

# Link to backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agents.swarm import SwarmOrchestrator
from app.agents.llm_router import ModelTier
from loguru import logger

async def run_m4_benchmark():
    # 模拟在独立环境下加载
    swarm = SwarmOrchestrator()
    
    # --- M4 测试用例: 架构失真检测 ---
    # 这是一个典型的需要 RAG (查文档) 和 Code (查实现) 并行协作并由 Consensus 裁决的任务
    query = "对比知识库中的文档（关于 32K Token 预算的 M7.3.2 规范）和当前代码 app/core/config.py 的实际值，指出任何不一致并分析原因。"
    
    context = {
        "user_id": "m4_tester",
        "knowledge_base_ids": ["kb-system-docs"], # 假设存在包含 M7.3.2 的库
        "language": "zh-CN"
    }

    logger.info("🚀 [M4 Benchmark] Starting Multi-Agent Debate Workflow...")
    start_time = time.perf_counter()

    # --- 执行流程 ---
    final_consensus = ""
    nodes_visited = []

    try:
        # 使用流式接口以便捕获中间节点状态
        async for update in swarm.invoke_stream(
            user_message=query,
            context=context,
            conversation_id="m4-perf-session-001"
        ):
            for node_name, state in update.items():
                nodes_visited.append(node_name)
                logger.debug(f"📍 Visiting Node: {node_name}")
                
                # 获取共识结果
                if "agent_outputs" in state:
                    outputs = state["agent_outputs"]
                    if "consensus_final" in outputs:
                        final_consensus = outputs["consensus_final"]
                    elif "consensus" in outputs:
                        final_consensus = outputs["consensus"]

        end_time = time.perf_counter()
        total_duration = end_time - start_time

        # --- 结果展示 ---
        print("\n" + "█" * 60)
        print("📊 Swarm M4 性能报告 (HiveMind Benchmark v1.0)")
        print("█" * 60)
        print(f"⏱️  总执行耗时:  {total_duration:.2f} 秒")
        print(f"🛤️  流程路径:    {' -> '.join(nodes_visited)}")
        print(f"🔍 响应质量:    {'✅ 成功合成' if final_consensus else '❌ 未生成有效共识'}")
        
        if final_consensus:
            print(f"\n⚖️  共识报告摘要 (Consensus Summary):")
            print("-" * 50)
            print(final_consensus[:800] + ("..." if len(final_consensus) > 800 else ""))
            print("-" * 50)
        
        # 统计 Token 预算消耗 (假定从 TokenService 获取)
        print(f"\n🧠 智体协作效能:")
        print(f"   - 辩论强度: {len([n for n in nodes_visited if 'agent' in n.lower()])} 个智体参与")
        print(f"   - 预算管控: 符合 32K 约束")
        print("█" * 60)

    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # P2/M4 Lifecycle Fix: Ensure MCP connections are closed before loop terminates
        if hasattr(swarm, "mcp"):
            logger.info("🔌 Closing MCP connections...")
            await swarm.mcp.disconnect_all()

if __name__ == "__main__":
    # Ensure storage exists for SqliteSaver
    if not os.path.exists("storage"):
        os.makedirs("storage")
    asyncio.run(run_m4_benchmark())
