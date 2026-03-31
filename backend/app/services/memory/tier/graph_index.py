"""
Tier-2 Memory: The Graph Overview Layer (GraphIndex).

职责:
- 从对话/文档文本中异步提取实体三元组，写入 Neo4j。
- 在检索时，从图谱中顺藤摸瓜找出指定实体的关联邻居（关系跳跃）。

注意事项:
- 所有 Neo4j 阻塞调用用 run_in_executor 包裹，防止阻塞 asyncio 事件循环。
- Neo4j 驱动不可用时，所有方法静默降级返回空，不干扰主业务。

参见: REGISTRY.md > 后端 > services/memory/tier > GraphIndex
参见: docs/design/tier2_graph_memory.md
所属模块: services.memory.tier
"""

import asyncio
import json

from loguru import logger

from app.core.graph_store import get_graph_store
from app.core.llm import get_llm_service


class GraphIndex:
    """
    Tier-2 图谱记忆层。

    使用场景:
        # 写入（在 MemoryService.add_memory 中）
        await graph_index.extract_and_store(doc_id, content)

        # 读取（在 ChatService/get_context 中）
        neighbors = await graph_index.get_neighborhood(["PostgreSQL", "Auth模块"])
    """

    def __init__(self):
        self.store = get_graph_store()

    def _is_available(self) -> bool:
        """检查 Neo4j 是否可用（开发环境下可能未部署）。"""
        return bool(self.store and getattr(self.store, "driver", None))

    async def extract_and_store(self, doc_id: str, content: str) -> None:
        """
        从文本中异步提取图结构（节点/边），注入 Neo4j。

        Args:
            doc_id: 内存段的唯一 ID（用于日志追踪）
            content: 原始文本内容
        """
        if not self._is_available():
            return

        llm = get_llm_service()
        prompt = f"""
        Analyze the following text and extract important entities and their relationships.
        Return ONLY valid JSON matching this exact schema:
        {{
            "nodes": [
                {{"id": "EntityName", "label": "Concept/Person/Technology", "name": "EntityName"}}
            ],
            "edges": [
                {{"source": "Entity1", "target": "Entity2", "type": "VERB_RELATION", "description": "how they relate"}}
            ]
        }}
        Text to analyze:
        {content}
        """

        try:
            resp_text = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(resp_text)
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            if nodes or edges:
                # 在线程池中执行阻塞的图数据库写入，保护事件循环
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: self.store.import_subgraph(nodes, edges))
                logger.info(f"🕸️ Tier-2 Indexed {len(nodes)} nodes, {len(edges)} edges for doc: {doc_id}.")
        except Exception as e:
            logger.warning(f"Tier-2 graph extraction failed for {doc_id}: {e}")

    async def get_neighborhood(self, entity_names: list[str], depth: int = 1) -> list[str]:
        """
        查询 Neo4j 中指定实体集合的图谱邻居（关系跳跃），组装为自然语言描述列表。

        Args:
            entity_names: 实体名称列表（通常来自 Tier-1 Radar 提取的标签）
            depth: 跳跃深度，当前固定 1 跳

        Returns:
            List[str]: 每行一个关系描述: "(A) -[REL]-> (B)  /* 描述 */"
                       Neo4j 不可用或无结果时返回 []
        """
        if not self._is_available() or not entity_names:
            return []

        safe_entities = [str(x).strip() for x in entity_names if x and x.strip()]
        if not safe_entities:
            return []

        cypher = """
        MATCH (a)-[r]-(b)
        WHERE a.name IN $entities OR a.id IN $entities
        RETURN a.id AS source, type(r) AS rel, b.id AS target, r.description AS descr
        LIMIT 15
        """

        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, lambda: self.store.query(cypher, {"entities": safe_entities}))

            neighborhood_str = []
            for item in results:
                src = item.get("source", "Unknown")
                rel = item.get("rel", "RELATED")
                tgt = item.get("target", "Unknown")
                desc = item.get("descr", "")
                line = f"({src}) -[{rel}]-> ({tgt})"
                if desc:
                    line += f"  /* {desc} */"
                neighborhood_str.append(line)

            return neighborhood_str
        except Exception as e:
            logger.warning(f"Tier-2 graph neighborhood query failed: {e}")
            return []

    async def record_agent_preference(self, agent_name: str, user_feedback: str) -> None:
        """
        从用户反馈中异步提取开发规范/风格偏好（特别是注释和代码风格），固化为图谱长期记忆。
        """
        if not self._is_available() or not user_feedback.strip():
            return

        llm = get_llm_service()
        prompt = f"""
        Analyze the user's feedback and extract explicit programming preferences, style guides, or rules (especially regarding code structure, naming conventions, or comment styles).
        Return ONLY valid JSON matching this schema:
        {{
            "preferences": [
                {{"category": "COMMENT_STYLE | NAMING | ARCHITECTURE | ERROR_HANDLING | OTHER", "rule": "The specific rule to follow", "confidence": 0.9}}
            ]
        }}
        User Feedback:
        {user_feedback}
        """

        try:
            resp_text = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(resp_text)
            preferences = data.get("preferences", [])
            
            if preferences:
                cypher = """
                MERGE (agent:IntelligenceNode {name: $agent_name})
                ON CREATE SET agent.type = 'Worker', agent.status = 'active'
                
                WITH agent
                UNWIND $preferences AS pref
                
                // 创建或更新偏好认知节点
                MERGE (prefNode:CognitiveAsset {id: 'PREF_' + pref.category, type: 'Preference'})
                SET prefNode.rule = pref.rule,
                    prefNode.confidence = pref.confidence,
                    prefNode.last_updated = datetime()
                
                // 将 Agent 与这个偏好灵魂绑定
                MERGE (agent)-[r:FOLLOWS_STYLE]->(prefNode)
                SET r.weight = prefNode.confidence
                """
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    lambda: self.store.query(cypher, {"agent_name": agent_name, "preferences": preferences})
                )
                logger.info(f"🧠 Tier-2 Indexed {len(preferences)} style preferences for agent '{agent_name}'.")
        except Exception as e:
            logger.warning(f"Tier-2 style preference extraction failed for {agent_name}: {e}")

    async def get_agent_preferences(self, agent_name: str, limit: int = 5) -> list[str]:
        """
        在启动 Agent 前，从图谱中召回与其相关的长期开发和注释偏好。
        """
        if not self._is_available():
            return []

        cypher = """
        MATCH (agent:IntelligenceNode {name: $agent_name})-[:FOLLOWS_STYLE]->(pref:CognitiveAsset {type: 'Preference'})
        WHERE pref.confidence >= 0.5
        RETURN pref.category AS category, pref.rule AS rule
        ORDER BY pref.confidence DESC, pref.last_updated DESC
        LIMIT $limit
        """
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: self.store.query(cypher, {"agent_name": agent_name, "limit": limit})
            )
            
            preferences_str = []
            for item in results:
                cat = item.get("category", "RULE")
                rule = item.get("rule", "")
                preferences_str.append(f"- [{cat}] {rule}")
                
            return preferences_str
        except Exception as e:
            logger.warning(f"Tier-2 style preference retrieval failed: {e}")
            return []

    async def index_code_structure(self, doc_id: str, structure: dict[str, Any]) -> None:
        """
        M7.2.1/3: Code Vault - 将代码结构（类、方法、函数）持久化到图谱中。
        """
        if not self._is_available() or not structure:
            return

        nodes = []
        edges = []

        # 1. 文件节点
        nodes.append({"id": doc_id, "label": "CodeFile", "name": doc_id})

        # 2. 类及其方法
        for cls in structure.get("classes", []):
            cid = f"{doc_id}::class::{cls['name']}"
            nodes.append({
                "id": cid, 
                "label": "Class", 
                "name": cls['name'], 
                "docstring": cls.get("docstring") or "",
                "lineno": cls.get("lineno")
            })
            edges.append({"source": doc_id, "target": cid, "type": "CONTAINS_CLASS"})
            
            for m in cls.get("methods", []):
                mid = f"{cid}::method::{m}"
                nodes.append({"id": mid, "label": "Method", "name": m})
                edges.append({"source": cid, "target": mid, "type": "HAS_METHOD"})

        # 3. 独立函数
        for fn in structure.get("functions", []):
            fid = f"{doc_id}::function::{fn['name']}"
            nodes.append({
                "id": fid, 
                "label": "Function", 
                "name": fn['name'],
                "docstring": fn.get("docstring") or "",
                "lineno": fn.get("lineno"),
                "params": ", ".join(fn.get("args", []))
            })
            edges.append({"source": doc_id, "target": fid, "type": "CONTAINS_FUNCTION"})

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.store.import_subgraph(nodes, edges))
            logger.info(f"🏗️  M7.2 CodeVault: Indexed structural assets for {doc_id} ({len(nodes)} assets)")
        except Exception as e:
            logger.warning(f"CodeVault indexing failed for {doc_id}: {e}")


# 单例访问
graph_index = GraphIndex()
