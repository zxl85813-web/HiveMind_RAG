"""
Refinement Lab — 检索优化实验室核心逻辑。

职责:
1. 从 BadCase 或 Trace 记录中提取样本。
2. 并行执行多种优化策略 (Measures Tournament)。
3. 对比分数并给出“进化建议”。
"""

import asyncio
import time
from typing import List, Dict, Any
from loguru import logger
from sqlmodel import select, desc
from pydantic import BaseModel

from app.core.database import get_db_session
from app.models.evaluation import BadCase
from app.services.rag_gateway import RAGGateway
from app.services.quality_governance import QualityGovernanceService

class LabResult(BaseModel):
    query: str
    baseline_score: float
    experiment_results: Dict[str, float] # strategy -> max_score
    winner: str
    improvement: float

class RefinementLab:
    """
    [AEC-L1] 实验室：通过对比试验寻找最优进化路径。
    """

    def __init__(self):
        self.gateway = RAGGateway()

    async def fetch_samples(self, limit: int = 10) -> List[str]:
        """从 BadCase 数据库中提取最近的不满案例作为样本。"""
        async for session in get_db_session():
            stmt = select(BadCase).order_by(desc(BadCase.created_at)).limit(limit)
            res = await session.exec(stmt)
            return [bc.question for bc in res.all()]
        return []

    async def run_tournament(self, queries: List[str], strategies: List[str]) -> List[Dict[str, Any]]:
        """
        [Tournament] 策略大比拼。
        """
        results = []
        for query in queries:
            logger.info(f"🧪 [Lab] Testing query: {query[:30]}...")
            query_stats = {"query": query, "scores": {}}
            
            # 对比不同的策略
            tasks = []
            for strategy in strategies:
                tasks.append(self._test_strategy(query, strategy))
            
            # 并行执行
            strategy_scores = await asyncio.gather(*tasks)
            for strategy, score in zip(strategies, strategy_scores):
                query_stats["scores"][strategy] = score
            
            results.append(query_stats)
            # 适当休眠，防止压垮模型
            await asyncio.sleep(0.5)
            
        return results

    async def _test_strategy(self, query: str, strategy_variant: str) -> float:
        """测试单个策略并返回最大相关性分数。"""
        try:
            # 这里通过 variant 注入不同的 HCAR 处理逻辑
            # 目前 RAGGateway 已支持不同的检索策略
            res = await self.gateway.retrieve(
                query=query, 
                kb_ids=["default"], # 默认测试主知识库
                strategy="hybrid" if strategy_variant == "baseline" else "vector",
                top_k=5
            )
            return res.quality.max_score
        except Exception as e:
            logger.error(f"Lab test failed for {strategy_variant}: {e}")
            return 0.0

    def generate_recommendation(self, results: List[Dict[str, Any]]) -> str:
        """根据实验结果生成自动化的改进建议。"""
        # 简单的统计逻辑：哪个策略在更多 Query 下拿到了最高分
        wins = {}
        for res in results:
            best_strategy = max(res["scores"], key=res["scores"].get)
            wins[best_strategy] = wins.get(best_strategy, 0) + 1
        
        overall_winner = max(wins, key=wins.get)
        improvement_msg = f"🏆 实验室结论：策略 '{overall_winner}' 表现最佳，在 {wins[overall_winner]}/{len(results)} 的案例中胜出。建议在生产环境开启该措施。"
        return improvement_msg
