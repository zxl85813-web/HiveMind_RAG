"""
分层记忆服务 (Multi-Tier Memory Service).

架构分层:
    Tier 1 (Hot Radar)    — InMemoryAbstractIndex，毫秒级标签集合交集路由
    Tier 2 (Graph Layer)  — Neo4j 图谱，实体关系跳跃检索
    Tier 3 (Deep Vector)  — ChromaDB 向量数据库，语义精排检索

写入流: add_memory()
    └─► Tier-1: asyncio.create_task(_extract_and_index_abstract)
    └─► Tier-2: asyncio.create_task(graph_index.extract_and_store)
    └─► Tier-3: memory_collection.add(...)  (同步，ChromaDB 本地)

读取流: get_context(query)
    1. Tier-1 Radar 路由 → 得到摘要列表 + tags
    2. Tier-2 图谱邻居  → 以 tags 为起点捞取关联圈
    3. Tier-3 向量检索  → 精确召回细节 Chunk
    4. 用户画像 (USER.md) + 今日日志兜底

所属模块: services.memory
参见: REGISTRY.md > 后端 > services > MemoryService
参见: docs/design/multi_tier_memory.md
"""

import asyncio
from collections.abc import Coroutine
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from loguru import logger
from pydantic import BaseModel, Field

# --- Memory Schemas (ARM-P1) ---


class RoleMemory(BaseModel):
    """
    群体层记忆 (ARM-P1-1).
    存储域内术语、风险偏好、固定模板等。
    """

    role_id: str
    terms: dict[str, str] = Field(default_factory=dict)
    risk_bias: list[str] = Field(default_factory=list)
    output_templates: dict[str, str] = Field(default_factory=dict)


class PersonalMemory(BaseModel):
    """
    个人层记忆 (ARM-P1-2).
    存储个性化偏好、历史上下文概括、常用资源权重。
    """

    user_id: str
    language: str = "zh"
    style_preference: str = "professional"
    project_contexts: list[str] = Field(default_factory=list)
    favorite_kb_ids: list[str] = Field(default_factory=list)


DATA_DIR = Path("data/memories")

# Tier-3: 本地向量存储（ChromaDB）
chroma_client = chromadb.PersistentClient(path="./start_data/chroma_db")
memory_collection = chroma_client.get_or_create_collection(name="agent_memories")


class MemoryService:
    """
    三层渐进式记忆引擎 — 模拟人类的记忆回溯过程。

    初始化参数:
        user_id: 用户 ID，用于隔离每个用户的记忆数据。

    使用方式:
        svc = MemoryService(user_id="user-abc")
        await svc.add_memory("Python asyncio 踩坑", metadata={"role": "user"})
        context = await svc.get_context("asyncio 相关的 bug")

    参见: REGISTRY.md > 后端 > services > MemoryService
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_dir = DATA_DIR / user_id
        self.logs_dir = self.user_dir / "logs"
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._ensure_directories()

    def _load_role_memory(self, role_id: str) -> RoleMemory:
        """Load role-specific shared memory (ARM-P1-1)."""
        role_dir = DATA_DIR / "roles"
        role_dir.mkdir(parents=True, exist_ok=True)
        path = role_dir / f"{role_id}.json"
        if path.exists():
            try:
                import json

                with open(path, encoding="utf-8", errors="replace") as f:
                    return RoleMemory(**json.load(f))
            except Exception as e:
                logger.error(f"Failed to load role memory for {role_id}: {e}")
        return RoleMemory(role_id=role_id)

    def save_role_memory(self, memory: RoleMemory) -> None:
        """Save role-specific shared memory (ARM-P1-1)."""
        role_dir = DATA_DIR / "roles"
        role_dir.mkdir(parents=True, exist_ok=True)
        path = role_dir / f"{memory.role_id}.json"
        try:
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(memory.model_dump(), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved role memory for {memory.role_id}")
        except Exception as e:
            logger.error(f"Failed to save role memory for {memory.role_id}: {e}")

    def _load_personal_memory(self) -> PersonalMemory:
        """Load user-specific personal memory (ARM-P1-2)."""
        path = self.user_dir / "personal_memory.json"
        if path.exists():
            try:
                import json

                with open(path, encoding="utf-8", errors="replace") as f:
                    return PersonalMemory(**json.load(f))
            except Exception as e:
                logger.error(f"Failed to load personal memory for {self.user_id}: {e}")
        return PersonalMemory(user_id=self.user_id)

    def save_personal_memory(self, memory: PersonalMemory) -> None:
        """Save user-specific personal memory (ARM-P1-2)."""
        path = self.user_dir / "personal_memory.json"
        try:
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(memory.model_dump(), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved personal memory for {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save personal memory for {self.user_id}: {e}")

    def _track_task(self, coro: Coroutine[Any, Any, Any]) -> None:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _ensure_directories(self):
        """确保用户记忆目录结构存在。"""
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        for file in ["USER.md", "KNOWLEDGE.md"]:
            fpath = self.user_dir / file
            if not fpath.exists():
                fpath.write_text(f"# {file.split('.')[0]}\n\n", encoding="utf-8")

    def _get_daily_log_path(self, date_str: str | None = None) -> Path:
        """获取今日日志文件路径（Ephemeral Memory）。"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return self.logs_dir / f"{date_str}.md"

    # ─────────────────────────────────────────────
    # 写入流 (Write Path)
    # ─────────────────────────────────────────────

    async def _extract_and_index_abstract(self, doc_id: str, content: str, role: str):
        """
        [Tier-1] 用 LLM 提取摘要 + 标签，写入内存倒排索引。
        由 add_memory 以 fire-and-forget 方式异步触发。
        """
        import json

        from app.core.llm import get_llm_service
        from app.services.memory.tier.abstract_index import abstract_index

        llm = get_llm_service()
        prompt = f"""
        Analyze the following memory segment and extract metadata in JSON format EXACTLY as below:
        {{
            "title": "Short title, max 5 words",
            "tags": ["tag1", "tag2"],
            "type": "{"user_query" if role == "user" else "ai_response"}"
        }}
        Content:
        {content}
        """
        try:
            resp = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(resp)
            abstract_index.add_abstract(
                doc_id=doc_id,
                title=data.get("title", "Untitled Fragment"),
                doc_type=data.get("type", "log"),
                tags=data.get("tags", ["general"]),
            )
            logger.info(f"⚡ Tier-1 Indexed | {data.get('title')} | Tags: {data.get('tags')}")
        except Exception as e:
            logger.warning(f"Tier-1 abstract extraction failed for {doc_id}: {e}")
            # Fallback: 以基础分类兜底入库
            from app.services.memory.tier.abstract_index import abstract_index

            abstract_index.add_abstract(doc_id, "Memory Fragment", role, ["fallback"])

    async def add_memory(self, content: str, metadata: dict[str, Any] | None = None):
        """
        将一段记忆写入所有三层存储。

        Args:
            content: 记忆内容文本
            metadata: 附加信息，支持 {"role": "user"/"assistant", "source": "daily_log" 等}

        写入策略:
            - Tier-1 (Abstract): fire-and-forget 异步 LLM 提取
            - Tier-2 (Graph): fire-and-forget 异步 LLM 提取 + Neo4j 写入
            - Tier-3 (Vector): 同步写入 ChromaDB（本地，极快）
        """
        if not content.strip():
            return

        doc_id = f"{self.user_id}-{int(datetime.now().timestamp() * 1000)}"
        meta = metadata or {}
        role = meta.get("role", "system")
        meta.update({"user_id": self.user_id, "timestamp": datetime.now().isoformat()})

        # Tier-0: Value Density Evaluation (GOV-003 Memory Governance)
        from app.core.algorithms.memory_governance import memory_governance_service

        density = await memory_governance_service.evaluate_density(content)
        meta.update({
            "value_score": density.score,
            "tier_target": density.tier_recommendation,
            "governance_reason": density.reasoning
        })

        logger.info(f"⚖️ [MemoryGov] Density: {density.score:.2f} ({density.tier_recommendation})")

        # Tier-1: 摘要索引 (Abstract Index)
        # Threshold: Only for ABSTRACT or GRAPH recommendations (Score > 0.3)
        if density.score > 0.3 or density.tier_recommendation in ["ABSTRACT", "GRAPH"]:
            self._track_task(self._extract_and_index_abstract(doc_id, content, role))
        else:
            logger.debug(f"⏭️ Skipping Tier-1 for low-value memory: {doc_id}")

        # Tier-2: 图谱提取 (Graph Index)
        # Threshold: Only for GRAPH recommendations (Score > 0.7)
        if density.score > 0.7 or density.tier_recommendation == "GRAPH":
            from app.services.memory.tier.graph_index import graph_index
            self._track_task(graph_index.extract_and_store(doc_id, content))
        else:
            logger.debug(f"⏭️ Skipping Tier-2 for low-value memory: {doc_id}")

        # Tier-3: 向量存储（同步，本地 ChromaDB，快） — Always persist as baseline
        memory_collection.add(documents=[content], metadatas=[meta], ids=[doc_id])
        logger.info(f"Memory persisted as {density.tier_recommendation} with score {density.score:.2f}")

    async def log_interaction(self, role: str, content: str):
        """
        将一次对话交互记录到今日日志，并触发记忆写入。
        Ephemeral Memory（日志）会随时间积累并被汇总到 Semantic Memory。
        """
        log_file = self._get_daily_log_path()
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"\n### [{timestamp}] {role.upper()}\n{content}\n"

        with open(log_file, "a", encoding="utf-8", errors="replace") as f:
            f.write(entry)

        # 仅对用户消息或较长的 AI 回复建索，避免噪声污染记忆库
        if role == "user" or len(content) > 50:
            await self.add_memory(content, metadata={"source": "daily_log", "role": role})

    async def update_user_profile(self, content: str):
        """写入用户画像（持久化记忆 USER.md），同时进行向量索引。"""
        file_path = self.user_dir / "USER.md"
        with open(file_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"\n- {content}")
        await self.add_memory(content, metadata={"source": "user_profile", "type": "fact"})

    # ─────────────────────────────────────────────
    # 读取流 (Read Path) — 三层级联检索
    # ─────────────────────────────────────────────

    async def get_context(self, query: str | None = None, role_id: str | None = None) -> str:
        """
        三层级联检索 + 记忆分层注入 (ARM-P1-3).
        组装出最丰富的上下文用于喂给 LLM。

        级联顺序:
            0. Role & Personal Memory — 认知对齐 (ARM-P1)
            1. 用户画像 (USER.md) — 始终优先注入
            2. Tier-1 Radar — 毫秒级摘要导航
            3. Tier-2 Graph — 图谱关系邻居
            4. Tier-3 Vector — 精确向量语义召回
            5. 今日日志 — 补充当前最新上下文

        Returns:
            str: 组合后的上下文字符串
        """
        from app.services.memory.episodic_service import episodic_memory_service
        from app.services.memory.tier.abstract_index import abstract_index
        from app.services.memory.tier.graph_index import graph_index

        context_blocks = []

        # ── Block E: Episodic Memory — 跨会话情节召回
        if query:
            episodes = await episodic_memory_service.recall_episodes(
                user_id=self.user_id, query=query, limit=3
            )
            if episodes:
                episodic_ctx = await episodic_memory_service.format_for_context(episodes)
                if episodic_ctx:
                    context_blocks.append(episodic_ctx)

        # ── Block 0: Role & Personal Memory (ARM-P1-3)
        if role_id:
            role_mem = self._load_role_memory(role_id)
            role_lines = []
            if role_mem.terms:
                role_lines.append(f"Domain Terms: {role_mem.terms}")
            if role_mem.risk_bias:
                role_lines.append(f"Risk Compliance Bias: {role_mem.risk_bias}")
            if role_lines:
                context_blocks.append(f"--- ROLE MEMORY ({role_id}) ---\n" + "\n".join(role_lines))

        persona = self._load_personal_memory()
        if persona.style_preference or persona.language != "zh":
            context_blocks.append(
                f"--- PERSONAL PREFERENCE ---\n- Style: {persona.style_preference}\n- Lang: {persona.language}"
            )

        # ── Block 1: 用户画像（始终最高优先）
        profile_path = self.user_dir / "USER.md"
        if profile_path.exists():
            profile = profile_path.read_text(encoding="utf-8", errors="replace")
            if profile.strip():
                context_blocks.append(f"--- USER PROFILE ---\n{profile}")

        if query:
            from app.services.memory.smart_grep_service import get_smart_grep_service
            
            # ── Block 2: Tier-1 Radar — 摘要级路由
            # ... (Block 2 & 3 implementation remains)
            radar_tags = await self._extract_query_tags(query)
            if radar_tags:
                hits = abstract_index.route_query(tags=radar_tags, limit=5)
                if hits:
                    radar_lines = "\n".join(
                        f"- [{h['type']}] {h['title']} (tags: {', '.join(h['tags'])})" for h in hits
                    )
                    context_blocks.append(f"--- HOT MEMORY (Tier-1 Radar) ---\n{radar_lines}")
                    for h in hits:
                        abstract_index.increment_hit(h["id"])

                # ── Block 3: Tier-2 Graph — 图谱关系邻居
                graph_neighbors = await graph_index.get_neighborhood(radar_tags)
                if graph_neighbors:
                    graph_lines = "\n".join(graph_neighbors)
                    context_blocks.append(f"--- KNOWLEDGE GRAPH (Tier-2) ---\n{graph_lines}")

            # ── Block 4: Tier-3 Deep Vector — 精确语义召回
            try:
                results = memory_collection.query(
                    query_texts=[query],
                    n_results=3,
                    where={"user_id": self.user_id},
                )
                if results.get("documents") and results["documents"][0]:
                    retrieved = "\n---\n".join(results["documents"][0])
                    context_blocks.append(f"--- DEEP MEMORY (Tier-3 Vector) ---\n{retrieved}")
            except Exception as e:
                logger.warning(f"Tier-3 vector search failed: {e}")

            # ── Block 4.5: SmartGrep — 传统高召回检索 (BM25 + Fuzzy)
            hot_hits = 0
            try:
                grep_svc = get_smart_grep_service()
                grep_results = await grep_svc.search(query, user_id=self.user_id, limit=3, mode="auto")
                if grep_results:
                    hot_hits = len(grep_results)
                    grep_lines = []
                    for r in grep_results:
                        snippet = r.content.replace("\n", " ")[:150]
                        grep_lines.append(f"- [{r.method}] {r.filename}: ...{snippet}...")
                    context_blocks.append(f"--- LOG EVIDENCE (SmartGrep) ---\n" + "\n".join(grep_lines))
            except Exception as e:
                logger.warning(f"SmartGrep integration failed: {e}")

            # ── Block 4.6: Tier-5 Global Knowledge — 全局 ES 冷检索 (非必要不启动)
            # 判定策略：如果个人热记忆 (Vector + Grep) 命中极少，或者查询涉及全局/手册类词汇
            global_triggers = ["standard", "spec", "manual", "guide", "policy", "api reference", "规范", "手册"]
            should_query_global = (hot_hits < 2) or any(k in query.lower() for k in global_triggers)

            if should_query_global:
                try:
                    from app.services.retrieval.es_service import get_global_knowledge_service
                    es_svc = get_global_knowledge_service()
                    # 仅在 ES 实际可用时建立连接
                    global_results = await es_svc.global_search(query, limit=2)
                    if global_results:
                        global_lines = []
                        for gr in global_results:
                            global_lines.append(f"- [{gr.index}] {gr.title or gr.id}: {gr.content}")
                        context_blocks.append(f"--- GLOBAL KNOWLEDGE (Tier-5 ES) ---\n" + "\n".join(global_lines))
                except Exception as e:
                    logger.warning(f"Tier-5 global search failed: {e}")

        # ── Block 5: 今日日志 — Ephemeral / 最近上下文
        daily_log = self._get_daily_log_path()

        if daily_log.exists():
            logs = daily_log.read_text(encoding="utf-8", errors="replace")[-2000:]
            if logs.strip():
                context_blocks.append(f"--- TODAY'S LOG (Ephemeral) ---\n...{logs}")


        return "\n\n".join(context_blocks)

    async def _extract_query_tags(self, query: str) -> list[str]:
        """
        [辅助] 从用户查询中快速提取关键词（作为 Tier-1 Radar 检索的标签）。
        使用 FAST 级别模型以降低延迟。失败时静默返回空列表。
        """
        import json

        from app.core.llm import get_llm_service

        try:
            llm = get_llm_service()
            prompt = f"""Extract 2-4 lowercase technical keywords from this query.
Return ONLY a JSON array: ["keyword1", "keyword2"]
Query: {query}"""
            resp = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            tags = json.loads(resp)
            return [t.lower().strip() for t in tags if isinstance(t, str)]
        except Exception:
            return []

    async def search_memory(self, query: str, limit: int = 5) -> list[str]:
        """
        对外暴露给 Agent Tools 使用的直接向量搜索接口。
        （简单场景不需要完整的 get_context，直接检索 Tier-3 即可）
        """
        try:
            results = memory_collection.query(query_texts=[query], n_results=limit, where={"user_id": self.user_id})
            return results["documents"][0] if results.get("documents") else []
        except Exception as e:
            logger.warning(f"search_memory failed: {e}")
            return []
