import asyncio
import sys
from pathlib import Path
import uuid

# 🏗️ [Path Fix]
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.logging import trace_id_var, get_trace_logger
from app.services.memory.smart_grep_service import get_smart_grep_service
from app.services.governance.prompt_service import prompt_service

logger = get_trace_logger("test.unclog")

async def test_golden_path():
    """
    黄金流程验证：
    Trace -> Prompt Registry -> Service -> DB/Redis (Mock)
    """
    # 1. 链路染色
    test_trace = f"unclog-{uuid.uuid4().hex[:6]}"
    trace_id_var.set(test_trace)
    print(f"\n🧬 [Step 1] Trace Activated: {test_trace}")

    # 2. 验证 Prompt 注册表
    print(f"🛰️ [Step 2] Fetching Prompt from Registry...")
    p_content = await prompt_service.get_prompt("smart_grep_expansion")
    if p_content:
        print(f"✅ [Prompt] Loaded: {p_content[:40]}...")
    else:
        print("❌ [Prompt] Failed to load prompt from Registry!")
        return

    # 3. 驱动推理流 (SmartGrep)
    print(f"🧪 [Step 3] Executing SmartGrep Expansion...")
    service = get_smart_grep_service()
    # 注意：这里会触发 LLM 调用，通过 Mock 或 真实 API
    # 为验证染色，我们主要看日志输出
    try:
        # 模拟模式：这里我们只看它是否走到了格式化 Prompt 这一步
        # 由于我们没有填真实的 LLM KEY，我们预期它在 LLM 调用时报错，但前面的链路应是通的
        results = await service.search("database migration", mode="llm")
        print(f"✅ [Flow] Search completed with {len(results)} hits.")
    except Exception as e:
        # 如果报错，正好检查错误日志中是否带有 trace_id
        print(f"ℹ️ [Flow] Expected LLM Interruption: {str(e)[:50]}")
    
    print("\n" + "="*80)
    print(f"✨ UNCLOGGED: Check your logs for trace_id='{test_trace}' and SQL comments!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_golden_path())
