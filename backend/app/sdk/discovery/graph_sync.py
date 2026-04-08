import os
from typing import List
from app.sdk.core import logger
from app.sdk.core.graph_store import get_graph_store
from app.sdk.spec_engine import get_spec_engine

class GraphSyncManager:
    """
    规格-图谱同步器。
    负责将 Spec 实体及其引用关系同步至 Neo4j。
    """
    def __init__(self):
        self.store = get_graph_store()
        self.spec_engine = get_spec_engine()

    async def sync_all_specs(self) -> int:
        """同步规格节点及其关系"""
        logger.info("GraphSync: Synchronizing specifications and relationships to Neo4j...")
        
        # 1. 扫描与节点同步
        self.spec_engine.scan_all()
        entities = self.spec_engine.registry
        count = 0
        
        # 第一阶段：原子化同步所有节点
        for entity_id, entity in entities.items():
            label = self._get_node_label_for_category(entity.category)
            query = (
                f"MERGE (n:{label} {{id: $entity_id}}) "
                f"SET n.path = $path, n.name = $name, n.last_sync = timestamp()"
            )
            await self.store.execute_query(query, {"entity_id": entity_id, "path": entity.file_path, "name": os.path.basename(entity.file_path)})
            count += 1

        # 第二阶段：建立引用关系
        rel_count = 0
        for entity_id, entity in entities.items():
            for ref_id in entity.references:
                if ref_id == entity_id: continue # 跳过自引用
                
                # 我们假设被引用的 ID 在系统中已经作为节点存在
                query = (
                    "MATCH (a {id: $src_id}), (b {id: $target_id}) "
                    "MERGE (a)-[r:REFERENCES]->(b) "
                    "SET r.auto_discovered = true"
                )
                await self.store.execute_query(query, {"src_id": entity_id, "target_id": ref_id})
                rel_count += 1
        
        logger.info(f"GraphSync: Sync complete. Nodes: {count}, Relationships: {rel_count}")
        return count

    def _get_node_label_for_category(self, category: str) -> str:
        mapping = {"requirement": "Requirement", "design": "Design", "change": "SpecChange"}
        return mapping.get(category, "SoftwareAsset")

async def run_spec_sync():
    sync = GraphSyncManager()
    await sync.sync_all_specs()

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_spec_sync())
