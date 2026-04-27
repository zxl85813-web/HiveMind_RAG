
import asyncio
import time
import sys
from pathlib import Path

# Fix paths for imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.graph_store import get_graph_store
from loguru import logger

async def merge_drifted_ids():
    """
    🏗️ [P0-Hardening]: 解决 ID 漂移造成的“孤岛”问题。
    将旧格式 (path::ClassName) 统一转换为新格式 (path::class::ClassName)。
    """
    store = get_graph_store()
    
    logger.info("🕵️  正在检测并修复 ID 漂移...")

    # 1. 寻找旧格式的节点 (path::Name) 且非新格式 (不含 ::class:: 或 ::method::)
    # 策略：如果 ID 包含 :: 但不包含 ::class:: 或 ::method::，则尝试转换
    cypher = """
    MATCH (n:ArchNode)
    WHERE n.id CONTAINS '::' 
      AND NOT n.id CONTAINS '::class::' 
      AND NOT n.id CONTAINS '::method::'
      AND NOT n.id STARTS WITH 'SM:'
    WITH n, split(n.id, '::') as parts
    WHERE size(parts) = 2
    SET n.old_id = n.id,
        n.id = parts[0] + '::class::' + parts[1]
    RETURN count(n) as count
    """
    res = await store.execute_query(cypher)
    logger.success(f"✅ 已迁移 {res[0]['count']} 个旧格式类节点 ID")

    # 2. 补全缺失的连接 (File) -> (Class) [CONTAINS]
    # 策略：如果 ID 是 path::class::Name，确保它与 path 有 CONTAINS 关系
    link_cypher = """
    MATCH (c:ArchNode)
    WHERE c.id CONTAINS '::class::'
    WITH c, split(c.id, '::class::')[0] as fpath
    MATCH (f:File {id: fpath})
    MERGE (f)-[:CONTAINS]->(c)
    RETURN count(*) as count
    """
    res_link = await store.execute_query(link_cypher)
    logger.success(f"✅ 已补全 {res_link[0]['count']} 个文件到类的包含关系")

    # 3. 为方法节点补全 (Class) -> (Method) [HAS_METHOD]
    link_method = """
    MATCH (m:ArchNode)
    WHERE m.id CONTAINS '::method::'
    WITH m, split(m.id, '::method::')[0] as cid
    MATCH (c:ArchNode {id: cid})
    MERGE (c)-[:HAS_METHOD]->(m)
    RETURN count(*) as count
    """
    res_m = await store.execute_query(link_method)
    logger.success(f"✅ 已补全 {res_m[0]['count']} 个类到方法的包含关系")

    logger.info("🏆 ID 标准化与链路补全完成。")
    await store.close()

if __name__ == "__main__":
    asyncio.run(merge_drifted_ids())
