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

    def query(self, cypher: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        同步查询代理（用于 Legacy run_in_executor）。
        警告: 这实际上是在当前线程开启了一个新的事件循环运行，仅对 Legacy 代码提供支持。
        """
        import asyncio
        import threading

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.execute_query(cypher, parameters))
            finally:
                loop.close()

        # 如果已经在异步循环中，这种同步调用是极其危险的，但为了兼容旧代码暂留
        return asyncio.run(self.execute_query(cypher, parameters))

    def import_subgraph(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
        """
        批量导入子图（同步版，兼容旧代码）。
        """
        import asyncio
        
        async def _import():
            if not self.driver: return
            async with self.driver.session() as session:
                # 导入节点
                node_cypher = """
                UNWIND $nodes AS n
                MERGE (node:ArchNode {id: n.id})
                ON CREATE SET node.created_at = timestamp()
                SET node += n, node.updated_at = timestamp()
                WITH n, node
                CALL apoc.create.addLabels(node, [n.label]) YIELD node as labeledNode
                RETURN count(*)
                """
                # 如果没有 APOC，退回到基础标签
                try:
                    await session.run(node_cypher, {"nodes": nodes})
                except:
                    fallback_node_cypher = """
                    UNWIND $nodes AS n
                    MERGE (node:ArchNode {id: n.id})
                    SET node += n, node.updated_at = timestamp()
                    """
                    await session.run(fallback_node_cypher, {"nodes": nodes})
                
                # 导入关系
                edge_cypher = """
                UNWIND $edges AS e
                MATCH (s:ArchNode {id: e.source})
                MATCH (t:ArchNode {id: e.target})
                CALL apoc.create.relationship(s, e.type, {description: e.description}, t) YIELD rel
                RETURN count(*)
                """
                try:
                    await session.run(edge_cypher, {"edges": edges})
                except:
                    # 极简退回：固定类型
                    fallback_edge_cypher = """
                    UNWIND $edges AS e
                    MATCH (s:ArchNode {id: e.source})
                    MATCH (t:ArchNode {id: e.target})
                    MERGE (s)-[:RELATED]->(t)
                    """
                    await session.run(fallback_edge_cypher, {"edges": edges})

        asyncio.run(_import())

_graph_store = None

def get_graph_store() -> Neo4jStore:
    global _graph_store
    if not _graph_store:
        _graph_store = Neo4jStore()
    return _graph_store
