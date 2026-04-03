import sys
import asyncio
from datetime import datetime
from pathlib import Path

# 🏗️ [Path Fix]: Allow script to run independently
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

# 🛰️ [Standard]: Import logging context
from app.core.logging import get_trace_logger
from app.services.governance.budget_service import budget_service

logger = get_trace_logger("scripts.audit_llm_costs")

async def run_audit():
    """
    LLM 成本治理巡检任务。
    职责:
    1. 统计当前费用度量。
    2. 生成治理状态总结。
    3. 如果超额，返回非零状态码 (Gate Fail)。
    """
    print("\n" + "="*80)
    print("🛡️  HIVE-MIND LLM COST GOVERNANCE AUDIT")
    print("="*80)
    
    result = await budget_service.check_alerts()
    metrics = result["metrics"]
    
    # 1. 概览
    print(f"\n📈  OVERVIEW (UTC {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"    - Daily Spending:  ${metrics['daily_cost']:.4f} / Limit: ${metrics['daily_limit']:.2f}")
    print(f"    - Monthly Spending: ${metrics['monthly_cost']:.4f} / Limit: ${metrics['monthly_limit']:.2f}")
    print(f"    - Alert Status:    {result['status']}")

    # 2. 分模型明细
    print(f"\n📂  MODEL BREAKDOWN:")
    print(f"    {'Model Name':30} | Cost (USD)")
    print(f"    {'-'*30:30} | {'-'*10:10}")
    for model, cost in metrics["breakdown"].items():
        print(f"    {model:30} | ${cost:.4f}")

    # 3. 告警推送
    if result["alerts"]:
        print(f"\n🔔  ALERTS DETECTED ({len(result['alerts'])}):")
        for alert in result["alerts"]:
            print(f"    {alert}")
    else:
        print("\n✅  NO ALERTS DETECTED. Budget is healthy.")

    print("\n" + "="*80)
    
    if result["status"] == "EXCEEDED":
        print("❌  FAILED: Cost budget exceeded! Blocking next stage.")
        sys.exit(1)
    else:
        print("✅  CI Budget Audit Passed.")
        sys.exit(0)

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(run_audit())
