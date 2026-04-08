import functools
import os
import json
from typing import Any, Dict, List
from app.sdk.core.logging import logger
from app.sdk.core.graph_store import get_graph_store

class ComponentRegistry:
    """ HiveMind 系统组件动态注册中心 """
    def __init__(self):
        self.components: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, category: str, description: str, metadata: Dict[str, Any] | None = None):
        """
        代码装饰器入口：
        @register_component("MyService", category="Service", description="...")
        """
        def decorator(obj: Any):
            component_info = {
                "name": name,
                "category": category,
                "description": description,
                "path": f"{obj.__module__}.{obj.__name__}",
                "metadata": metadata or {}
            }
            self.components[name] = component_info
            logger.info(f"Registry: Discovered [{category}] {name} at {component_info['path']}")
            return obj
        return decorator

    async def sync_to_graph(self):
        """将所有发现的组件同步至 Neo4j 图谱"""
        if not self.components:
            logger.warning("Registry: No components found to sync. Skipping.")
            return
            
        store = get_graph_store()
        logger.info(f"Registry: STARTING sync for {len(self.components)} components...")
        
        for name, info in self.components.items():
            query = (
                "MERGE (c:SoftwareComponent {name: $name}) "
                "SET c.path = $path, "
                "    c.category = $category, "
                "    c.description = $description, "
                "    c.last_registered = timestamp() "
                "RETURN c"
            )
            await store.execute_query(query, {
                "name": name,
                "path": info["path"],
                "category": info["category"],
                "description": info["description"]
            })
            logger.info(f"Registry: Synced component [{name}] to graph.")
        
        logger.info("Registry: Graph synchronization FINISHED SUCCESSFULLY.")

# 全局单例
registry = ComponentRegistry()
register_component = registry.register
