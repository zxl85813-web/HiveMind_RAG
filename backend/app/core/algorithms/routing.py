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
        try:
            emb_service = get_embedding_service()
            embs = [emb_service.embed_query(u) for u in route.utterances]
            self._route_cache[route.name] = embs
        except Exception as e:
            # Fallback: store empty embeddings to allow startup to continue
            # The route will have zero similarity and fall back to default
            print(f"⚠️ Failed to compute embeddings for route '{route.name}': {e}")
            self._route_cache[route.name] = [[0.0] * 2048 for _ in route.utterances]

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


class VectorAgentRouter:
    """
    5.3 动态智能路由：向量Agent路由器。
    在 SwarmOrchestrator Supervisor 中作为「第 2.5 层」使用：
      关键字快速路径（Tier 0）→ 向量相似度（Tier 1, 本类）→ LLM（Tier 2）

    预先缓存每个 Agent 描述的 Embedding。每次路由请求只做一次 embed
    + N 次余弦运算，比 LLM 调用快 2~3 个数量级。
    如果最高相似度 < threshold，返回 None，由调用方继续降级到 LLM。
    """

    def __init__(self, default_threshold: float = 0.40) -> None:
        self._agents: dict[str, list[float]] = {}  # name → description embedding
        self.default_threshold = default_threshold

    def register_agent(self, name: str, description: str) -> None:
        """Pre-compute and cache the embedding for 'description'."""
        try:
            emb = get_embedding_service().embed_query(description)
            self._agents[name] = emb
        except Exception:
            # Embedding service may not be initialised at import time; skip silently.
            pass

    async def route(self, query: str, threshold: float | None = None) -> str | None:
        """
        Return the best-matching agent name, or None if confidence is too low.

        Args:
            query:     The user query string.
            threshold: Minimum cosine similarity (default: self.default_threshold).
        """
        if not self._agents:
            return None

        thr = threshold if threshold is not None else self.default_threshold
        try:
            query_emb = get_embedding_service().embed_query(query)
        except Exception:
            return None

        best_name, best_score = max(
            ((_n, _cosine_similarity(query_emb, _e)) for _n, _e in self._agents.items()),
            key=lambda x: x[1],
        )
        return best_name if best_score >= thr else None


vector_agent_router = VectorAgentRouter()
