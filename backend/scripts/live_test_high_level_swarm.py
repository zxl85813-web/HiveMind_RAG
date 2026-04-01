import asyncio
import sys
import os
import time
from loguru import logger

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

async def run_benchmark():
    logger.info("🧪 [Swarm High-Level Test] Initializing live test environment...")
    
    # 🌩️ [The Ultimate Test Query]: Detailed code analysis + comparative reasoning
    # This should trigger high complexity scoring (Budget=8)
    query = (
        "深度分析 HiveMind 项目中 swarm.py 的 _run_react_loop 逻辑，"
        "说明它是如何实现 asyncio.gather 并行执行工具调用的，并判断其资源回收是否安全。"
    )
    
    request = ChatRequest(
        message=query,
        execution_variant="react",  # 强行指定 ReAct 模式
        conversation_id=None
    )
    
    mock_user_id = "test-admin-001"
    
    logger.info(f"🚀 发送高维查询: {query[:60]}...")
    
    t0 = time.time()
    chunk_count = 0
    status_updates = []
    content_received = ""

    try:
        async for chunk in ChatService.chat_stream(request, user_id=mock_user_id):
            if chunk.startswith("data: "):
                try:
                    payload = chunk[6:].strip()
                    data = __import__("json").loads(payload)
                    
                    track = data.get("track")
                    if track == "status":
                        content = data.get("content", "")
                        status_updates.append(content)
                        # 打印实时的进度反馈
                        print(f"📡 [Status Update]: {content}")
                        
                    elif track == "content":
                        delta = data.get("delta", "")
                        content_received += delta
                        chunk_count += 1
                        
                    elif track == "done":
                        print("\n✅ [Swarm Done Signal Received]")
                        print(f"⏱️ 总端到端耗时 (E2E): {data.get('latency_ms', 0):.0f}ms")
                        
                except Exception as e:
                    print(f"⚠️ 解析 Chunk 失败: {e}")

    except Exception as e:
        logger.error(f"❌ 测试过程中发生致命错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*50)
    print("📊 [实验报告摘要]")
    print(f"1. 状态更新频次: {len(status_updates)} 次 (反映了并行任务与思维深度)")
    print(f"2. 提取的关键反馈: ")
    for s in status_updates[-5:]:  # 展示最后 5 个状态
        print(f"   - {s}")
    
    # --- 关键断言 (Logic Verification) ---
    has_budget_info = any("Budget" in s for s in status_updates)
    has_timing_info = any("Think=" in s for s in status_updates)
    
    print(f"3. 架构指标验证:")
    print(f"   - 自适应预算触发: {'✅ 成功' if has_budget_info else '❌ 失败'}")
    print(f"   - 并行计时上报: {'✅ 成功' if has_timing_info else '❌ 失败'}")
    print("="*50)

if __name__ == "__main__":
    # Ensure nested async loops work or run directly
    asyncio.run(run_benchmark())
