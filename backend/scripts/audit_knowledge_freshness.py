import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 🏗️ [Path Fix]: Allow script to run independently
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.logging import get_trace_logger
from app.services.knowledge.freshness_service import knowledge_freshness_service

logger = get_trace_logger("scripts.audit_freshness")

async def run_audit():
    """
    RAG 知识状态巡检。
    识别所有过期或需要审核的文档。
    """
    print("\n" + "="*80)
    print("🛡️  HIVE-MIND KNOWLEDGE FRESHNESS AUDIT")
    print("="*80)
    
    # 自动应用默认新鲜度 (如果尚未设置)
    # 这确保了脚本在初次运行时就能产生有意义的结果
    print("🔍 Checking and applying default freshness policies...")
    await knowledge_freshness_service.set_default_freshness(months=6)

    report = await knowledge_freshness_service.get_freshness_report()
    
    print(f"\n📊 KNOWLEDGE BASE PULSE (UTC {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"    - Total Documents:   {report['total_documents']}")
    print(f"    - Healthy (Fresh):   {report['healthy_count']}")
    print(f"    - Expired (Dead):    {report['expired_count']}")
    print(f"    - Stale (Needs Rev): {report['stale_count']}")

    if report["expired_details"]:
        print(f"\n🚨 EXPIRED DOCUMENTS (Action Required):")
        print(f"    {'ID':36} | {'Filename':30} | {'Expired At'}")
        print(f"    {'-'*36:36} | {'-'*30:30} | {'-'*20}")
        for doc in report["expired_details"]:
            print(f"    {doc['id']:36} | {doc['filename']:30} | {doc['expiry']}")
    else:
        print("\n✨ All documents are within their freshness window.")

    print("\n" + "="*80)
    print("✅ Freshness Audit Completed.")

if __name__ == "__main__":
    asyncio.run(run_audit())
