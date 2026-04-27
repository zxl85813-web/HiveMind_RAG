"""
Quality Governance Service — 检索质量治理与动态应对决策中心。

职责:
1. 分析 RAGGateway 返回的质量指标。
2. 根据质量等级 (FAIL/LOW_RELEVANCE) 决策应对措施。
3. 提供一组可插拔的“补救工具” (Measures)。
"""

from typing import Any, Dict, List
from loguru import logger
from pydantic import BaseModel

from app.schemas.knowledge_protocol import KnowledgeResponse, KnowledgeQuality

class GovernanceDecision(BaseModel):
    action: str              # retry | proceed | clarify | fallback
    reason: str
    suggested_measures: List[str]
    new_params: Dict[str, Any] = {}

class QualityGovernanceService:
    """
    [AEC-C1] 控制中心：决定系统何时需要“主动进化”。
    """

    @staticmethod
    def evaluate_and_decide(
        response: KnowledgeResponse, 
        attempt_count: int = 1
    ) -> GovernanceDecision:
        quality = response.quality
        
        # 1. 如果结果非常好，直接继续
        if quality.quality_tier in ["EXCELLENT", "GOOD"]:
            return GovernanceDecision(
                action="proceed",
                reason="Retrieval quality is satisfactory.",
                suggested_measures=[]
            )

        # 2. 如果结果不佳且是第一次尝试，建议“主动进化”重试
        if attempt_count < 2:
            if quality.quality_tier == "FAIL":
                return GovernanceDecision(
                    action="retry",
                    reason="No relevant results found. Triggering Query Expansion.",
                    suggested_measures=["query_expansion", "hyde"],
                    new_params={"top_k": 10, "strategy": "vector"} # 扩大半径
                )
            
            if quality.quality_tier == "LOW_RELEVANCE":
                return GovernanceDecision(
                    action="retry",
                    reason="Low relevance scores. Injecting Graph Context.",
                    suggested_measures=["graph_topology_boost", "memory_injection"],
                    new_params={"top_k": 5, "strategy": "hybrid"}
                )

        # 3. 如果重试后依然不佳，进入降级模式
        return GovernanceDecision(
            action="proceed",
            reason="Exhausted refinement attempts. Proceeding with best available context.",
            suggested_measures=["hallucination_warning"] # 提醒用户结果可能不准
        )

class RefinementMeasures:
    """
    [AEC-T1] 措施工具箱：具体的改写和增强算法。
    """
    
    @staticmethod
    async def expand_query(original_query: str, llm_service: Any) -> List[str]:
        """生成 3 个不同维度的搜索词。"""
        prompt = f"针对查询 '{original_query}'，生成 3 个语义差异化的搜索关键词，用逗号分隔。"
        res = await llm_service.chat_complete([{"role": "user", "content": prompt}])
        return [s.strip() for s in res.split(",")][:3]

    @staticmethod
    def boost_with_graph(query: str, graph_context: str) -> str:
        """将图谱拓扑信息强行注入查询。"""
        return f"{query} (关联架构上下文: {graph_context})"
