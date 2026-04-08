"""
Graph Store Interface — Neo4j Integration (Async Edition).
[Consolidated into app.sdk.core]
"""
from typing import Any, List, Dict
from app.sdk.core.config import settings
from app.sdk.core.logging import logger

try:
    from neo4j import AsyncGraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class Neo4jStore:
    """现代化的异步 Neo4j 存储接口"""
    def __init__(self):
        self.driver = None
        if not NEO4J_AVAILABLE:
            logger.warning("Neo4j driver not installed. Graph features will be disabled.")
            return

        uri = settings.NEO4J_URI
        user = settings.NEO4J_USER
        password = settings.NEO4J_PASSWORD

        try:
            self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"Initialized Async Neo4j Driver at {uri}")
        except Exception as e:
            logger.warning(f"Neo4j Init Failed: {e}")

    async def close(self):
        if self.driver:
            await self.driver.close()

    async def execute_query(self, cypher: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """执行异步 Cypher 查询"""
        if not self.driver:
            return []

        try:
            async with self.driver.session() as session:
                result = await session.run(cypher, parameters or {})
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Neo4j Query Error: {e}")
            return []

_graph_store = None

def get_graph_store() -> Neo4jStore:
    global _graph_store
    if not _graph_store:
        _graph_store = Neo4jStore()
    return _graph_store
