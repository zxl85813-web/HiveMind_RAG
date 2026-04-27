import asyncio
import sys
from pathlib import Path

# 将项目根目录加入路径
sys.path.append(str(Path(__file__).parent.parent))

from app.services.evaluation.refinement_lab import RefinementLab
from app.models.evaluation import BadCase
from app.core.database import get_db_session
from loguru import logger
from pydantic import BaseModel

async def setup_test_data():
    """预置一个测试用的 BadCase。"""
    try:
        async for session in get_db_session():
            # 创建一个模拟的失败案例
            test_case = BadCase(
                question="如何配置 HiveMind 的动态精炼 Agent？",
                bad_answer="暂无相关文档。",
                reason="Manual evaluation failure",
                status="pending"
            )
            session.add(test_case)
            await session.commit()
            logger.info("✅ 预置测试数据成功：BadCase 已加入数据库。")
            return
    except Exception as e:
        logger.error(f"Failed to setup test data: {e}")

async def run_verification():
    logger.info("🚀 开始验证 Refinement Lab 闭环...")
    
    # 1. 初始化实验室
    lab = RefinementLab()
    
    # 2. 提取样本
    samples = await lab.fetch_samples(limit=1)
    if not samples:
        logger.warning("⚠️ 未找到样本，请确认数据库中已有 BadCase。")
        return

    # 3. 运行策略锦标赛
    # 对比 Baseline 和 我们准备开启的策略
    strategies = ["baseline", "experimental_refine"]
    logger.info(f"🧪 正在对样本进行锦标赛对决: {samples[0]}")
    
    results = await lab.run_tournament(samples, strategies)
    
    # 4. 打印报告
    logger.info("📊 --- 实验结果报告 ---")
    for res in results:
        logger.info(f"Query: {res['query']}")
        for strategy, score in res['scores'].items():
            status = "🟢" if score > 0.3 else "🔴"
            logger.info(f"  - [{strategy}]: Score={score:.2f} {status}")
            
    recommendation = lab.generate_recommendation(results)
    logger.info(f"💡 AI 建议: {recommendation}")

async def main():
    # 1. 先置数据
    await setup_test_data()
    
    # 2. 再跑实验
    await run_verification()

if __name__ == "__main__":
    asyncio.run(main())
