"""
通用路由算法 (Semantic Router)
从硬编码逻辑脱离，基于特征向量的比对进行目标分发路由。
用于多智能体调度与资源分配网关降级。
"""

import math

from pydantic import BaseModel

from app.core.embeddings import get_embedding_service


class Route(BaseModel):
    name: str
    utterances: list[str]


class RoutingDecision(BaseModel):
    """标准的决定卡牌。"""

    target_node: str  # 路由至图谱 / 向量 / 某个具体 Agent 名称
    confidence: float  # 置信度 (基于 Cosine 或 LLM Softmax)
    reasoning: str | None  # 理由 (当使用 LLM 降级路由时提供溯源日志)


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


class SemanticRouter:
    """Semantic Vector Routing logic using EmbeddingService."""

    def __init__(self):
        self._route_cache: dict[str, list[list[float]]] = {}

    def add_route(self, route: Route):
        """Pre-compute and cache embeddings for a route."""
        emb_service = get_embedding_service()
        embs = [emb_service.embed_query(u) for u in route.utterances]
        self._route_cache[route.name] = embs

    async def route(self, text: str, routes: list[Route], threshold: float = 0.5) -> RoutingDecision:
        """
        基于用户输入决定流量走向最高匹配度的节点。
        """
        if not routes:
            return RoutingDecision(target_node="default", confidence=0.0, reasoning="No routes provided")

        emb_service = get_embedding_service()

        # Ensure all routes are cached
        for r in routes:
            if r.name not in self._route_cache:
                self.add_route(r)

        text_emb = emb_service.embed_query(text)

        best_route = None
        best_score = -1.0

        for r in routes:
            for r_emb in self._route_cache[r.name]:
                score = _cosine_similarity(text_emb, r_emb)
                if score > best_score:
                    best_score = score
                    best_route = r.name

        if best_route and best_score >= threshold:
            # logger.debug(f"SemanticRouter matched to route '{best_route}' with score {best_score:.3f}")
            return RoutingDecision(
                target_node=best_route,
                confidence=best_score,
                reasoning=f"Cosine similarity score {best_score:.3f} exceeded threshold {threshold}",
            )

        fallback_node = routes[0].name
        # logger.debug(f"SemanticRouter fallback: max score {best_score:.3f} below threshold {threshold}. Using '{fallback_node}'.")
        return RoutingDecision(
            target_node=fallback_node, confidence=best_score, reasoning="Below threshold, fallback used."
        )


semantic_router = SemanticRouter()
