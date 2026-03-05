# 🔌 HiveMind RAG 数据交互接口设计

> **核心问题：** RAG 系统的产出是"知识"，但目前它以原始文本字符串的形式交付给消费者。
> 这就像一个微服务返回 `"user: John, age: 30"` 而不是 `{"user": "John", "age": 30}`。
>
> 本文档设计一套 **结构化的知识交互协议**，让 Agent、Skill 和外部系统都能正确、高效地消费 RAG 的产出。

---

## 一、现状诊断：三个消费者，三种原始接口

```
┌─────────────────────────────────────────────────────────────────┐
│                    当前数据交互现状 (问题)                        │
│                                                                 │
│  消费者 1: Agent (_retrieval_node)                               │
│  ─────────────────────────────────────                         │
│  输入:  query (str)                                             │
│  输出:  context_str (str) → "--- DEEP CONTEXT ---\n[1] Source.."│
│  问题:  ❌ 纯文本拼接，无结构                                    │
│         ❌ 丢失了 rerank score                                  │
│         ❌ 丢失了 KB 来源信息                                    │
│         ❌ 无法让 Agent 按需过滤                                 │
│                                                                 │
│  消费者 2: Skill Tool (search_knowledge_base)                   │
│  ──────────────────────────────────────────                    │
│  输入:  query (str), top_k (int)                                │
│  输出:  str → "SOURCE: xxx\nCONTENT: yyy\n---\n..."            │
│  问题:  ❌ 返回纯字符串，Skill 无法程序化处理                    │
│         ❌ 没有走完整的 RetrievalPipeline                       │
│         ❌ 没有 ACL 过滤                                        │
│                                                                 │
│  消费者 3: REST API (/knowledge/{kb_id}/search)                 │
│  ─────────────────────────────────────────                     │
│  输入:  SearchRequest {query, top_k, search_type}               │
│  输出:  SearchResponse {results: [{content, metadata, score}]}  │
│  问题:  ⚠️ trace_log 返回固定占位符                              │
│         ⚠️ 缺少检索元信息 (耗时、KB 路由决策)                    │
│         ❌ 只支持单 KB 查询，不支持多 KB 联合                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、设计目标

```
┌─────────────────────────────────────────────────────────────────┐
│                     设计目标                                     │
│                                                                 │
│  1. 统一输出协议 (Unified Output Protocol)                       │
│     → 不管谁消费 RAG 的结果（Agent/Skill/API/外部系统），        │
│       都拿到同一个结构化的 KnowledgeResponse                     │
│                                                                 │
│  2. 多层接口 (Multi-Layer Interface)                             │
│     → L1: Agent 内部 (SwarmState 注入)                          │
│     → L2: Skill Tool (LangChain Tool 接口)                      │
│     → L3: REST API (HTTP 接口，标准 OpenAPI)                    │
│                                                                 │
│  3. 数据契约 (Data Contract)                                    │
│     → 每一层都基于同一个 Pydantic Schema                        │
│     → Schema 是"编译器的目标代码规格"                             │
│                                                                 │
│  4. 可观测 (Observable)                                          │
│     → 每次检索都携带完整的 trace 信息                            │
│     → 支持前端展示、调试、优化                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心数据契约 (Data Contract)

### 3.1 KnowledgeFragment — 知识片段（原子单位）

```python
# 文件: app/schemas/knowledge_protocol.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class FragmentSource(str, Enum):
    """知识片段的来源类型"""
    VECTOR = "vector"           # 向量检索命中
    GRAPH = "graph"             # 知识图谱跳转
    MEMORY = "memory"           # Agent 记忆层
    CACHE = "cache"             # 语义缓存命中


class KnowledgeFragment(BaseModel):
    """
    知识片段 — RAG 系统的原子输出单位。
    
    类比：这是"编译后的目标代码"的最小可执行单元。
    每个 Fragment 是一个自包含、可寻址、可审计的知识块。
    """
    # === 核心内容 ===
    content: str                                    # 知识片段的文本内容
    
    # === 溯源信息 (Source Map) ===
    source: FragmentSource = FragmentSource.VECTOR   # 来源类型
    document_name: str = ""                          # 原始文档名
    document_id: str = ""                            # 文档 ID (可追溯)
    kb_id: str = ""                                  # 所属知识库
    kb_name: str = ""                                # 知识库名称
    page: str = ""                                   # 页码/位置
    chunk_id: str = ""                               # Chunk ID (精确追溯)
    
    # === 质量信号 ===
    relevance_score: float = 0.0                     # rerank 得分 (0-1)
    freshness: str = "unknown"                       # 新鲜度: fresh/stale/unknown
    security_level: str = "public"                   # 安全级别: public/internal/confidential
    
    # === 元数据 ===
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 原始元数据透传
```

### 3.2 KnowledgeResponse — 知识响应（完整封装）

```python
class RetrievalMetrics(BaseModel):
    """检索过程的度量信息"""
    total_candidates: int = 0           # 召回候选数
    after_acl_filter: int = 0           # ACL 过滤后剩余
    after_rerank: int = 0               # 重排后最终返回
    latency_ms: float = 0.0             # 总耗时 (毫秒)
    kb_ids_queried: List[str] = Field(default_factory=list)   # 实际查询的 KB
    kb_ids_routed: List[str] = Field(default_factory=list)    # 路由器选择的 KB
    query_expanded: bool = False         # 是否做了查询扩展
    hyde_used: bool = False              # 是否使用了 HyDE
    graph_facts_injected: int = 0        # 注入的图谱事实数


class KnowledgeResponse(BaseModel):
    """
    RAG 系统的统一输出协议。
    
    无论消费者是 Agent、Skill 还是 REST API，都通过这个协议获取知识。
    这是"数据微服务"对外暴露的标准 API Response。
    
    设计原则：
    1. 自包含 — 不需要额外查询就能理解每个片段的来源和质量
    2. 可审计 — trace 信息完整记录每一步决策
    3. 可消费 — Agent 可以按 score 过滤，Skill 可以程序化处理
    """
    
    # === 核心输出 ===
    fragments: List[KnowledgeFragment] = Field(default_factory=list)
    
    # === 上下文摘要 (供 Agent/LLM 直接注入 Prompt) ===
    context_text: str = ""              # 拼接好的上下文文本 (便捷使用)
    citation_map: Dict[str, str] = Field(default_factory=dict)  # "[1]" → "文档A P3"
    
    # === 检索元信息 ===
    metrics: RetrievalMetrics = Field(default_factory=RetrievalMetrics)
    trace_log: List[str] = Field(default_factory=list)  # Pipeline 每步日志
    
    # === 查询理解 ===
    original_query: str = ""
    rewritten_query: str = ""
    query_intent: str = ""              # fact/comparison/summary/action
    sub_queries: List[str] = Field(default_factory=list)
    
    # === 状态标志 ===
    has_results: bool = False
    is_degraded: bool = False           # 是否降级模式 (某 KB 不可用)
    degradation_reason: str = ""
    
    def to_prompt_context(self) -> str:
        """生成 Agent 可直接注入 Prompt 的上下文字符串"""
        if not self.fragments:
            return "[No relevant knowledge found]"
        
        parts = []
        for i, frag in enumerate(self.fragments, 1):
            citation = f"[{i}]"
            source_info = f"{frag.document_name}"
            if frag.page:
                source_info += f" (P{frag.page})"
            
            parts.append(f"{citation} {source_info}\n{frag.content}")
            self.citation_map[citation] = source_info
            
        return "--- Retrieved Knowledge ---\n" + "\n\n".join(parts)
    
    def to_tool_output(self) -> str:
        """生成 Skill Tool 可返回给 LLM 的格式化字符串"""
        if not self.fragments:
            return "No matching knowledge found."
        
        parts = []
        for frag in self.fragments:
            parts.append(
                f"📄 SOURCE: {frag.document_name} | KB: {frag.kb_name} | "
                f"Score: {frag.relevance_score:.2f}\n"
                f"CONTENT: {frag.content}"
            )
        
        summary = f"\n[Found {len(self.fragments)} results from {len(self.metrics.kb_ids_queried)} knowledge bases]"
        return "\n\n---\n\n".join(parts) + summary
```

---

## 四、三层消费者接口设计

### 4.1 L1 — Agent 内部接口 (SwarmState 注入)

```python
# 改造 _retrieval_node 的输出

# ═══ 改造前 (当前代码) ═══
# context_str += f"[{i+1}] Source: {file_name} (Page {page})\n{d.page_content}\n"
# return {"context_data": context_str, ...}

# ═══ 改造后 ═══
async def _retrieval_node(self, state: SwarmState) -> dict:
    """Retrieval node — 使用 KnowledgeResponse 结构化输出"""
    
    # ... (路由 + 检索逻辑不变) ...
    
    # 构建结构化响应
    from app.schemas.knowledge_protocol import (
        KnowledgeResponse, KnowledgeFragment, 
        FragmentSource, RetrievalMetrics
    )
    
    response = KnowledgeResponse(
        original_query=query,
        metrics=RetrievalMetrics(
            kb_ids_queried=kb_ids,
            kb_ids_routed=kb_ids,
        )
    )
    
    if docs:
        for i, d in enumerate(docs):
            frag = KnowledgeFragment(
                content=d.page_content,
                source=FragmentSource.VECTOR,
                document_name=d.metadata.get("file_name", "Unknown"),
                document_id=d.metadata.get("doc_id", ""),
                kb_id=d.metadata.get("kb_id", ""),
                page=str(d.metadata.get("page", "")),
                chunk_id=d.metadata.get("chunk_id", ""),
                relevance_score=d.metadata.get("rerank_score", 0.0),
                metadata=d.metadata,
            )
            response.fragments.append(frag)
        
        response.has_results = True
        response.context_text = response.to_prompt_context()
        response.metrics.after_rerank = len(docs)
    
    response.trace_log = retrieval_logs
    
    return {
        "context_data": response.context_text,      # 兼容旧 Prompt 注入
        "knowledge_response": response.model_dump(), # 结构化数据 (新)
        "last_node_id": node_id,
        "retrieval_trace": response.trace_log,
        "retrieved_docs": [f.model_dump() for f in response.fragments],
    }
```

### 4.2 L2 — Skill Tool 接口

```python
# 改造 search_knowledge_base Tool

from langchain_core.tools import tool

@tool
async def retrieve_knowledge(
    query: str,
    kb_ids: list[str] | None = None,
    top_k: int = 5,
    top_n: int = 3,
    include_graph: bool = True,
) -> str:
    """
    从知识库中检索相关知识。
    
    这是 Agent 主动检索知识的标准工具。
    与 _retrieval_node 的被动注入不同，这个工具允许 Agent
    在 ReAct 循环中按需补充上下文。
    
    Args:
        query: 检索查询
        kb_ids: 指定知识库 ID 列表 (不指定则自动路由)
        top_k: 召回候选数
        top_n: 最终返回数
        include_graph: 是否包含知识图谱信息
    
    Returns:
        结构化的知识检索结果
    """
    from app.services.rag_gateway import RAGGateway
    
    gateway = RAGGateway()
    response = await gateway.retrieve(
        query=query,
        kb_ids=kb_ids,
        top_k=top_k,
        top_n=top_n,
        include_graph=include_graph,
    )
    
    # 返回给 LLM 的格式化文本
    return response.to_tool_output()
```

### 4.3 L3 — REST API 接口

```python
# 新增/改造 API endpoint

# ═══ 请求 Schema ═══
class RetrieveRequest(BaseModel):
    """统一检索请求"""
    query: str
    kb_ids: list[str] | None = None          # 不指定则自动路由
    top_k: int = Field(default=20, le=100)   # 召回数
    top_n: int = Field(default=5, le=20)     # 返回数
    search_type: str = "hybrid"               # vector/bm25/hybrid
    include_graph: bool = True                # 是否包含图谱
    include_trace: bool = False               # 是否返回 trace (调试用)
    filters: dict[str, Any] = {}             # 元数据过滤条件


# ═══ 端点定义 ═══

# 1. 智能检索 (自动路由)
@router.post("/retrieve", response_model=ApiResponse[KnowledgeResponse])
async def smart_retrieve(
    request: RetrieveRequest,
    current_user: User = Depends(get_current_user),
):
    """
    POST /knowledge/retrieve
    
    统一检索入口 — 支持自动 KB 路由、多 KB 联合检索。
    
    Returns: KnowledgeResponse (结构化知识响应)
    """
    gateway = RAGGateway()
    response = await gateway.retrieve(
        query=request.query,
        kb_ids=request.kb_ids,
        top_k=request.top_k,
        top_n=request.top_n,
        search_type=request.search_type,
        include_graph=request.include_graph,
        user_id=current_user.id,
    )
    
    if not request.include_trace:
        response.trace_log = []  # 生产环境不返回 trace
    
    return ApiResponse.ok(data=response)


# 2. 指定 KB 检索 (保留现有端点，增强输出)
@router.post("/{kb_id}/search", response_model=ApiResponse[KnowledgeResponse])
async def search_single_kb(
    kb_id: str,
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    POST /knowledge/{kb_id}/search
    
    针对特定 KB 的检索 (保留兼容性，输出升级为 KnowledgeResponse)
    """
    gateway = RAGGateway()
    response = await gateway.retrieve(
        query=request.query,
        kb_ids=[kb_id],
        top_k=request.top_k,
        search_type=request.search_type,
        user_id=current_user.id,
    )
    return ApiResponse.ok(data=response)
```

---

## 五、RAG Gateway — 统一服务层

```python
# 新文件: app/services/rag_gateway.py

"""
RAG Gateway — 统一的知识检索服务入口。

这是"数据微服务"的 API Gateway。
所有知识检索请求（无论来自 Agent、Skill 还是 REST API）
都通过这个 Gateway 进入 RAG Pipeline。

设计原则 (微服务治理)：
1. 统一入口 — 所有消费者使用同一个服务
2. 路由抽象 — 消费者不需要知道 KB 的物理位置
3. 容错降级 — 某个 KB 不可用时自动降级
4. 可观测    — 每次调用都有完整 trace
"""

import time
from typing import List, Optional, Dict, Any
from loguru import logger
from app.schemas.knowledge_protocol import (
    KnowledgeResponse, KnowledgeFragment,
    FragmentSource, RetrievalMetrics,
)


class RAGGateway:
    """
    RAG 系统的统一服务网关。
    
    微服务类比：
    - KnowledgeBaseSelector = Service Discovery
    - RetrievalPipeline = Service Mesh  
    - RAGGateway = API Gateway
    - KnowledgeResponse = Response Protocol
    """
    
    def __init__(self):
        from app.services.retrieval.pipeline import get_retrieval_service
        self._pipeline = get_retrieval_service()
    
    async def retrieve(
        self,
        query: str,
        kb_ids: Optional[List[str]] = None,
        top_k: int = 20,
        top_n: int = 5,
        search_type: str = "hybrid",
        include_graph: bool = True,
        user_id: Optional[str] = None,
        is_admin: bool = False,
    ) -> KnowledgeResponse:
        """
        统一检索入口。
        
        流程：
        1. KB 路由 (如果未指定 kb_ids)
        2. kb_id → vector_collection 映射
        3. 执行 RetrievalPipeline
        4. 构建 KnowledgeResponse
        """
        start_time = time.time()
        
        response = KnowledgeResponse(
            original_query=query,
            metrics=RetrievalMetrics(),
        )
        
        try:
            # 1. KB 路由
            routed_kb_ids = kb_ids or []
            if not routed_kb_ids:
                from app.services.retrieval.routing import KnowledgeBaseSelector
                selector = KnowledgeBaseSelector()
                selected = await selector.select_kbs(query)
                routed_kb_ids = [kb.id for kb in selected]
            
            response.metrics.kb_ids_routed = routed_kb_ids
            
            # 2. kb_id → collection 映射
            from sqlmodel import Session
            from app.core.database import engine
            from app.models.knowledge import KnowledgeBase
            
            collection_map = {}  # collection_name → (kb_id, kb_name)
            collection_names = []
            
            with Session(engine) as session:
                for kid in routed_kb_ids:
                    kb = session.get(KnowledgeBase, kid)
                    if kb and kb.vector_collection:
                        collection_names.append(kb.vector_collection)
                        collection_map[kb.vector_collection] = (kb.id, kb.name)
            
            response.metrics.kb_ids_queried = list(collection_map.keys())
            
            if not collection_names:
                response.has_results = False
                response.trace_log.append("[Gateway] No valid KB collections found")
                return response
            
            # 3. 执行 Pipeline
            docs, trace_log = await self._pipeline.run(
                query=query,
                collection_names=collection_names,
                top_k=top_k,
                top_n=top_n,
                search_type=search_type,
                user_id=user_id,
                is_admin=is_admin,
            )
            
            response.trace_log = trace_log
            
            # 4. 构建 Fragments
            for doc in docs:
                doc_kb_id = doc.metadata.get("kb_id", "")
                kb_info = collection_map.get(doc_kb_id, ("", ""))
                
                frag = KnowledgeFragment(
                    content=doc.page_content,
                    source=FragmentSource.GRAPH
                        if doc.metadata.get("type") == "graph"
                        else FragmentSource.VECTOR,
                    document_name=doc.metadata.get("file_name", 
                        doc.metadata.get("source", "Unknown")),
                    document_id=doc.metadata.get("doc_id", ""),
                    kb_id=doc_kb_id or kb_info[0],
                    kb_name=kb_info[1] if kb_info[1] else "",
                    page=str(doc.metadata.get("page", "")),
                    chunk_id=doc.metadata.get("chunk_id", ""),
                    relevance_score=doc.metadata.get("rerank_score", 0.0),
                    security_level=doc.metadata.get("security_level", "public"),
                    metadata=doc.metadata,
                )
                response.fragments.append(frag)
            
            response.has_results = len(response.fragments) > 0
            response.context_text = response.to_prompt_context()
            
            # 5. 填充指标
            elapsed = (time.time() - start_time) * 1000
            response.metrics.latency_ms = round(elapsed, 2)
            response.metrics.after_rerank = len(response.fragments)
            
            # 从 trace 提取查询理解信息
            for log_entry in trace_log:
                if "Intent:" in log_entry:
                    response.query_intent = log_entry.split("Intent:")[1].split(",")[0].strip()
                if "rewritten:" in log_entry.lower():
                    response.rewritten_query = log_entry.split(":")[-1].strip()
                if "sub-queries:" in log_entry.lower():
                    response.metrics.query_expanded = True
                    
        except Exception as e:
            logger.error(f"RAGGateway error: {e}")
            response.is_degraded = True
            response.degradation_reason = str(e)
            response.trace_log.append(f"[Gateway] Critical error: {e}")
        
        return response
```

---

## 六、写入侧接口设计

### 6.1 入库接口 (Ingestion API)

```
当前已有端点 (保持不变):
  POST /knowledge/documents                      → 上传文档
  POST /knowledge/{kb_id}/documents/{doc_id}      → 关联文档到 KB + 触发编译

需要增强的:
  POST /knowledge/{kb_id}/documents/{doc_id}/reindex  → 重新编译 (增量)
  POST /knowledge/{kb_id}/sync                        → 强制同步/全量重编译
  GET  /knowledge/{kb_id}/health                      → KB 健康度查询
```

### 6.2 事件通知接口 (Event Notification)

```python
# WebSocket 推送：知识库变更事件

class KBEventType(str, Enum):
    DOC_INDEXED = "doc_indexed"           # 文档入库完成
    DOC_FAILED = "doc_failed"             # 文档入库失败
    KB_VERSION_CHANGED = "kb_version"     # KB 版本更新
    KB_HEALTH_CHANGED = "kb_health"       # KB 健康度变化

class KBEvent(BaseModel):
    event_type: KBEventType
    kb_id: str
    kb_name: str
    doc_id: str | None = None
    message: str
    timestamp: datetime
    
# 推送时机：
# 1. index_document_task 完成时 → DOC_INDEXED / DOC_FAILED  
# 2. KnowledgeService.link_document_to_kb → KB_VERSION_CHANGED
# 3. 未来 HealthCheck 检测到异常 → KB_HEALTH_CHANGED
```

---

## 七、完整 API 契约一览

```
┌──────────────────────────────────────────────────────────────────┐
│                  HiveMind Knowledge API 契约                     │
│                                                                  │
│  ═══ 读取侧 (Retrieval) ═══                                     │
│                                                                  │
│  POST /knowledge/retrieve                                        │
│    → 智能检索 (自动路由 + 多 KB 联合)                             │
│    → Input:  RetrieveRequest                                     │
│    → Output: KnowledgeResponse                                   │
│                                                                  │
│  POST /knowledge/{kb_id}/search                                  │
│    → 单 KB 检索 (指定目标)                                       │
│    → Input:  SearchRequest                                       │
│    → Output: KnowledgeResponse                                   │
│                                                                  │
│  GET  /knowledge/{kb_id}/graph                                   │
│    → 知识图谱查询 (已有)                                         │
│    → Output: {nodes, links}                                      │
│                                                                  │
│  ═══ 写入侧 (Ingestion) ═══                                     │
│                                                                  │
│  POST /knowledge/documents                                       │
│    → 上传文档到全局文档库 (已有)                                  │
│    → Output: DocumentResponse                                    │
│                                                                  │
│  POST /knowledge/{kb_id}/documents/{doc_id}                      │
│    → 关联文档 + 触发编译 (已有)                                   │
│    → Output: KnowledgeBaseDocumentLink                            │
│                                                                  │
│  POST /knowledge/{kb_id}/documents/{doc_id}/reindex              │
│    → 重新编译单文档 (新增)                                        │
│    → Output: {job_id, status}                                    │
│                                                                  │
│  ═══ 管理侧 (Governance) ═══                                    │
│                                                                  │
│  GET  /knowledge/{kb_id}/health                                  │
│    → KB 健康度查询 (新增)                                        │
│    → Output: {score, doc_count, last_indexed, issues}            │
│                                                                  │
│  GET  /knowledge/{kb_id}/stats                                   │
│    → KB 统计信息 (新增)                                          │
│    → Output: {doc_count, chunk_count, avg_score, version}        │
│                                                                  │
│  ═══ 内部接口 (Agent/Skill 专用) ═══                             │
│                                                                  │
│  RAGGateway.retrieve(...)                                        │
│    → Python 调用 (无 HTTP 开销)                                  │
│    → Input:  同 RetrieveRequest                                  │
│    → Output: KnowledgeResponse (Pydantic 对象)                   │
│                                                                  │
│  @tool retrieve_knowledge(...)                                   │
│    → LangChain Tool (Agent ReAct 循环中调用)                     │
│    → Output: str (to_tool_output 格式化文本)                     │
│                                                                  │
│  SwarmState["knowledge_response"]                                │
│    → _retrieval_node 自动注入                                    │
│    → 结构化 dict (KnowledgeResponse.model_dump)                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 八、与架构哲学的映射

```
┌─────────────────┬────────────────────────────────────────────┐
│  架构理念         │  在数据交互接口中的体现                     │
├─────────────────┼────────────────────────────────────────────┤
│ Skill = 纯函数   │ KnowledgeResponse 是纯数据对象              │
│                 │ to_prompt_context() 是纯转换函数             │
│                 │ to_tool_output() 是纯转换函数                │
├─────────────────┼────────────────────────────────────────────┤
│ Agent = 副作用   │ RAGGateway.retrieve() 是副作用函数           │
│                 │ 它执行 I/O (查 DB、查向量库、调 LLM)        │
│                 │ 但通过 KnowledgeResponse 封装输出             │
├─────────────────┼────────────────────────────────────────────┤
│ 治理 = 编译器    │ 入库 Pipeline 是"编译器"                    │
│                 │ KnowledgeResponse 是"编译产物的运行时接口"    │
├─────────────────┼────────────────────────────────────────────┤
│ 治理 = 微服务    │ RAGGateway = API Gateway                   │
│                 │ KnowledgeResponse = Response Protocol       │
│                 │ RetrievalMetrics = Service Metrics           │
│                 │ is_degraded = Circuit Breaker 信号           │
├─────────────────┼────────────────────────────────────────────┤
│ 数据契约         │ KnowledgeFragment = Protobuf/OpenAPI        │
│                 │ 所有消费者使用同一个 Schema                   │
│                 │ 结构化 > 字符串拼接                          │
└─────────────────┴────────────────────────────────────────────┘
```

---

## 九、实施路径

### Phase 1: 建立数据契约 (1 day)
1. 创建 `app/schemas/knowledge_protocol.py` — 定义 Schema
2. 创建 `app/services/rag_gateway.py` — 统一服务层

### Phase 2: 改造三个消费者 (2 days)
1. 改造 `_retrieval_node` — 输出 KnowledgeResponse
2. 改造 `search_knowledge_base` Tool → `retrieve_knowledge`
3. 升级 `/knowledge/{kb_id}/search` API 输出

### Phase 3: 新增接口 (1 day)
1. 新增 `POST /knowledge/retrieve` (智能检索)
2. 新增 `POST /knowledge/{kb_id}/documents/{doc_id}/reindex`
3. 新增 `GET /knowledge/{kb_id}/health`
