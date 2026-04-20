
import asyncio
import time
import os
import sys
from pathlib import Path

# Fix paths for imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.graph_store import get_graph_store
from loguru import logger

async def solidify_metadata():
    """
    🏗️ [P0-Hardening]: 固化图谱元数据。
    解决资产列表中的 "Unknown" 问题，并确保所有 ArchNode 具有合规的路径与时间戳。
    """
    store = get_graph_store()
    now_ms = int(time.time() * 1000)
    
    logger.info("🕵️  正在启动图谱元数据固化程序...")

    # 1. 修复缺失的时间戳
    time_cypher = """
    MATCH (n:ArchNode)
    WHERE n.created_at IS NULL OR n.created_at = 0
    SET n.created_at = $now
    RETURN count(n) as count
    """
    res_time = await store.execute_query(time_cypher, {"now": now_ms})
    logger.success(f"✅ 已修复 {res_time[0]['count']} 个缺失时间戳的节点")

    # 2. 启发式修复缺失的路径 (Path)
    # 策略：
    # - 如果 ID 包含 /，则 ID 本身即路径
    # - 如果 ID 包含 :: (逻辑资产)，则前缀通常是文件路径
    # - 否则标记为 SystemGenerated
    path_cypher = """
    MATCH (n:ArchNode)
    WHERE n.path IS NULL OR n.path = "Unknown" OR n.path = ""
    WITH n, 
         CASE 
            WHEN n.id CONTAINS '/' THEN n.id 
            WHEN n.id CONTAINS '::' THEN split(n.id, '::')[0]
            ELSE 'AutoExtract'
         END as inferred_path
    SET n.path = inferred_path
    RETURN count(n) as count
    """
    res_path = await store.execute_query(path_cypher)
    logger.success(f"✅ 已修复 {res_path[0]['count']} 个缺失物理路径的节点")

    # 3. 补全标签缺失 (确保所有 ArchNode 至少有一个具体的业务标签)
    label_cypher = """
    MATCH (n:ArchNode)
    WHERE size(labels(n)) = 1
    SET n:LogicEntity
    RETURN count(n) as count
    """
    res_label = await store.execute_query(label_cypher)
    logger.info(f"ℹ️  已为 {res_label[0]['count']} 个孤立资产打上 :LogicEntity 标签")

    logger.info("🏆 元数据治理完成。")
    await store.close()

if __name__ == "__main__":
    try:
        asyncio.run(solidify_metadata())
    except Exception as e:
        logger.error(f"❌ 固化任务失败: {e}")
