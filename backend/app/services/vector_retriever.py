from app.sdk.discovery.registry import register_component
from app.sdk.core.logging import logger

@register_component(
    "VectorRetriever",
    category="Service",
    description="高性能向量语义检索器，支持多路召回与重排序。"
)
class VectorRetriever:
    def __init__(self):
        logger.info("VectorRetriever initialized.")

    async def retrieve(self, query: str):
        return f"Results for: {query}"
