"""
Agent Swarm Orchestrator — the "Hive Mind" that coordinates all agents.

Architecture:
    Supervisor Agent (LangGraph StateGraph)
        ├── RAG Agent        — Knowledge base retrieval & answer
        ├── SQL Agent        — Structured data queries
        ├── Web Agent        — Internet search & augmentation
        ├── Code Agent       — Code generation & execution
        ├── Reflection Agent — Self-evaluation & error correction
        └── Custom Agents    — Dynamically registered agents

Integrations:
    - PromptEngine: 四层 Prompt 组合 (base → role → task → context)
    - Artifact: 结构化输出，支持 Pipeline 跨 Swarm 通信
    - Model Hints: 不同 Agent 可使用不同模型

The Supervisor analyzes user intent and routes to appropriate agent(s).
Multiple agents may collaborate on a single request.
All agents share a common memory space.
"""

# ruff: noqa: E501, N806

import asyncio
import json
from collections.abc import AsyncGenerator, Coroutine
from typing import Annotated, Any, Callable, Literal, TypedDict


def merge_dict_outputs(left: dict[str, str], right: dict[str, str]) -> dict[str, str]:
    """[M5.1.2] Reducer for merging agent outputs without overwriting."""
    new_state = (left or {}).copy()
    new_state.update(right or {})
    return new_state


from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.agentic_search import SEARCH_TOOLS
from app.agents.bus import get_agent_bus
from app.agents.compactor import ContextCompactor
from app.agents.llm_router import LLMRouter, ModelTier
from app.agents.memory import SharedMemoryManager
from app.agents.tools import NATIVE_TOOLS
from app.core.algorithms.routing import vector_agent_router
from app.core.config import settings
from app.schemas.auth import AuthorizationContext
from app.services.cache_service import CacheService
from app.services.evaluation.multi_grader import MultiGraderEval
from app.services.sandbox.tool_sandbox import ToolSandbox
from app.core.token_service import TokenService

# ============================================================
#  Agent Definition
# ============================================================


class AgentDefinition:
    """
    Definition of an agent in the swarm.

    Attributes:
        name: Unique agent identifier
        description: What this agent does (used by Supervisor for routing)
        skills: List of skill names this agent can use
        tools: List of tools (MCP + native) available to this agent
        model_hint: Preferred model type ("fast", "balanced", "reasoning")
    """

    def __init__(
        self,
        name: str,
        description: str,
        skills: list[str] | None = None,
        tools: list[Any] | None = None,
        model_hint: str | None = None,
    ):
        self.name = name
        self.description = description
        self.skills = skills or []
        self.tools = tools or []
        self.model_hint = model_hint  # 从 PromptEngine YAML 或手动指定


# ============================================================
#  State Definition
# ============================================================


class SwarmState(TypedDict):
    """
    Shared state for the Agent Swarm.

    This is the "Blackboard" where all agents read/write context.
    """

    # Conversation history (all messages)
    messages: Annotated[list[BaseMessage], add_messages]

    # The next agent to route to ("rag", "code", "end", etc.)
    next_step: str

    # Agent outputs for debate/collaboration
    # Key: Agent Name, Value: Their latest output/opinion
    agent_outputs: Annotated[dict[str, str], merge_dict_outputs]

    # [M5.1.4] Distributed Trace ID for inter-agent communication tracking
    swarm_trace_id: str

    # Uncertainty level (0.0 - 1.0)
    # High uncertainty triggers debate or user clarification
    uncertainty_level: float

    # Current task description (can be refined by Supervisor)
    current_task: str

    # Conversation ID for persistence/TODO linkage
    conversation_id: str

    # Number of reflection/retry cycles
    reflection_count: int

    # The original user query (preserved across loops)
    original_query: str

    # Context data retrieved from various memory tiers (RAG, Graph, Radar)
    context_data: str

    # Specific Knowledge Base constraints
    kb_ids: list[str]

    # Prompt/Retrieval experiment variants for A/B testing
    prompt_variant: str
    retrieval_variant: str

    # --- A/B Test: Execution Mode (GOV-EXP-001) ---
    # "monolithic": current behavior — one LLM call thinks everything, then loops tools
    # "react":      distributed — Think(short) → Act → Observe → Think(short) → ...
    execution_variant: str

    # --- A/B Observability: per-request thinking time telemetry (ms) ---
    # Populated by _create_agent_node; read by reflection for A/B comparison.
    thinking_time_ms: list[float]
    tool_time_ms: list[float]

    # [M5.1.5] Pinned Messages that MUST NOT be compacted (e.g. Decisions, User Preferences)
    pinned_messages: list[str]

    # --- GOV-EXP-002: Dynamic Reasoning Budget (M4.2.8) ---
    reasoning_budget: int | None # Number of ReAct steps allowed

    # Track Last Node Id for visual trace
    last_node_id: str

    # P2: RAG Retrieval Trace Logs
    retrieval_trace: list[str]
    retrieved_docs: list[dict]

    # --- Phase 7: Permission Guard ---
    user_id: str | None
    auth_context: AuthorizationContext | None

    # --- P1: Routing Watchdog Flag ---
    force_reasoning_tier: bool

    # --- FE-GOV-003: i18n Bridge ---
    language: str | None


class ScopedStateView:
    """
    [M5.1.1] Scoped State Sharing.
    Defines and enforces which state fields are visible to specific agents.
    Prevents 'Context Pollution' and accidental data leaks.
    """

    # Default visibility for any agent
    DEFAULT_SCOPE = [
        "messages",
        "current_task",
        "original_query",
        "conversation_id",
        "user_id",
        "language",
        "pinned_messages",
    ]

    # Specialized visibility for core nodes
    AGENT_SCOPES = {
        "supervisor": [
            "messages",
            "next_step",
            "agent_outputs",
            "uncertainty_level",
            "original_query",
            "context_data",
            "kb_ids",
            "conversation_id",
            "user_id",
            "auth_context",
            "force_reasoning_tier",
            "language",
        ],
        "rag": [
            "messages",
            "original_query",
            "kb_ids",
            "retrieval_trace",
            "retrieved_docs",
            "context_data",
            "language",
        ],
        "sql": [
            "messages",
            "original_query",
            "current_task",
            "context_data",
        ],
        "code": [
            "messages",
            "original_query",
            "current_task",
            "context_data",
            "reasoning_budget",
            "execution_variant",
        ],
        "reflection": [
            "messages",
            "original_query",
            "agent_outputs",
            "uncertainty_level",
            "current_task",
            "reflection_count",
            "context_data",
        ],
    }

    @classmethod
    def filter(cls, state: dict, agent_name: str) -> dict:
        """Filters the global state to a subset allowed for the specific agent."""
        # Normalize agent name (e.g. 'code_agent_1' -> 'code')
        base_name = agent_name.split("_")[0].lower()
        allowed_keys = cls.AGENT_SCOPES.get(base_name, cls.DEFAULT_SCOPE)

        filtered = {k: v for k, v in state.items() if k in allowed_keys}

        # Debug log for significant omissions (optional)
        omitted = set(state.keys()) - set(allowed_keys)
        if omitted:
            logger.trace(f"🛡️ [ScopedState] {agent_name} view filtered. Omitted {len(omitted)} keys.")

        return filtered



# ============================================================
#  Structured Outputs
# ============================================================


class RoutingDecision(BaseModel):
    """Supervisor's decision on how to route the request."""

    next_agent: str = Field(description="The name of the next agent to invoke, or 'FINISH'")
    uncertainty: float = Field(description="Confidence score (0.0 = confident, 1.0 = uncertain)")
    reasoning: str = Field(description="Reason for this routing decision")
    task_refinement: str = Field(description="Refined description of the task for the agent")
    # --- Phase 5: Task Decomposition (Architecture Layer 4 Intelligence) ---
    planned_steps: list[str] = Field(
        default_factory=list, description="Optional: decompose complex task into sub-tasks"
    )
    # --- Phase 4: Parallel Collaboration (M4.2.5) ---
    parallel_agents: list[str] = Field(
        default_factory=list, description="Optional: invoke multiple agents in parallel for debate or speed"
    )


class ReflectionResult(BaseModel):
    """Reflection node's quality assessment."""

    quality_score: float = Field(description="0.0-1.0 quality assessment")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    verdict: str = Field(description="APPROVE | REVISE | ESCALATE")
    trigger_reasoning_tier: bool = Field(default=False, description="Whether to escalate to the highest reasoning LLM tier")


# ============================================================
#  Swarm Orchestrator
# ============================================================


class SwarmOrchestrator:
    """
    The central coordinator for the Agent Swarm.

    Responsibilities:
    - Register and manage agents
    - Build and compile the LangGraph state graph
    - Route user requests to appropriate agents (via PromptEngine)
    - Coordinate agent collaboration
    - Trigger reflection cycles
    - Produce structured Artifacts for Pipeline integration
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}
        self._graph = None  # Compiled LangGraph StateGraph
        self._background_tasks: set[asyncio.Task[Any]] = set()

        # --- LLM Router (Tiered Selection) ---
        self.router = LLMRouter()

        # --- Memory Manager ---
        self.memory = SharedMemoryManager()

        # --- PromptEngine (lazy import to avoid circular deps) ---
        self._prompt_engine = None

        # --- Services (Lazy load) ---
        self._retriever = None

        # --- MCP Manager (P2 Migration) ---
        from app.agents.mcp_manager import MCPManager

        self.mcp = MCPManager()

        # --- Skill Registry ---
        from app.skills.registry import SkillRegistry
        self.skills = SkillRegistry()

        # --- Agent Streaming Engine (OPT-2) ---
        from app.agents.engine import AgentEngine
        self.engine = AgentEngine(self)

        # --- Tool Indexing (OPT-6 Lite) ---
        from app.agents.tool_index import ToolIndex, set_tool_index
        # All potential tools for indexing
        all_potential_tools = list(NATIVE_TOOLS)
        # In a real impl, we'd also index MCP and Skill tools here
        self.tool_index = ToolIndex(all_potential_tools)
        set_tool_index(self.tool_index)

        # --- Internal Message Bus (OPT-3) ---
        self.bus = get_agent_bus()

        # --- History Compactor (OPT-5 + P0 Hardening) ---
        self.compactor = ContextCompactor(
            llm=self.router.get_model(tier=ModelTier.SIMPLE), # Use cheaper model for summarization
            threshold_tokens=int(settings.CONTEXT_WINDOW_LIMIT * settings.BUDGET_HISTORY_RATIO)
        )

        self._initialized = False
        self._init_lock = asyncio.Lock()

        logger.info("🐝 SwarmOrchestrator initialized with Tiered LLM Routing, MCP, Skills, Bus, and Compactor")

    def _track_task(self, coro: Coroutine[Any, Any, Any]) -> None:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def ensure_initialized(self):
        """Ensure MCP, Tool Index, and Graph are stable (M4 Fix)."""
        if self._initialized:
            return
        async with self._init_lock:
            if not self._initialized:
                logger.info("📡 [Swarm] Initializing persistent assets (MCP/Embeddings/Graph)...")
                await self.mcp.load_config("mcp_config.json")
                await self.mcp.connect_all()
                await self.tool_index.initialize_embeddings()
                # Ensure the graph is built
                await self.build_graph()
                self._initialized = True

    # ============================================================
    #  Agent Management
    # ============================================================

    def get_agents(self) -> dict[str, AgentDefinition]:
        """Return all registered agents."""
        return self._agents

    # LLM Management is now delegated to self.router

    def _get_llm_for_agent(self, agent_def: AgentDefinition) -> BaseChatModel:
        """
        Get the appropriate LLM for an agent based on model_hint.
        """
        hint = agent_def.model_hint or "balanced"

        # Map string hint to ModelTier enum
        try:
            tier = ModelTier(hint.lower())
        except ValueError:
            tier = ModelTier.MEDIUM

        return self.router.get_model(tier)

    # ============================================================
    #  PromptEngine Access
    # ============================================================

    @property
    def prompt_engine(self):
        """Lazy-load PromptEngine to avoid circular imports."""
        if self._prompt_engine is None:
            from app.prompts.engine import prompt_engine

            self._prompt_engine = prompt_engine
        return self._prompt_engine

    # ============================================================
    #  Agent Registration
    # ============================================================

    def register_agent(self, agent: AgentDefinition) -> None:
        """Register a new agent into the swarm."""
        # Try to load model_hint from PromptEngine YAML if not specified
        if not agent.model_hint:
            agent.model_hint = self.prompt_engine.get_model_hint(agent.name)

        self._agents[agent.name] = agent
        logger.info(f"Agent registered: {agent.name} (model_hint={agent.model_hint})")
        # 5.3 向量路由：同步注册到 VectorAgentRouter 缓存（Tier 1 快速路径）
        if agent.description:
            vector_agent_router.register_agent(agent.name, agent.description)

    def unregister_agent(self, name: str) -> None:
        """Remove an agent from the swarm."""
        if name in self._agents:
            self._agents.pop(name, None)
            logger.info(f"Agent unregistered: {name}")

    def list_agents(self) -> list[AgentDefinition]:
        """List all registered agents."""
        return list(self._agents.values())

    # ============================================================
    #  Graph Construction
    # ============================================================

    async def build_graph(self) -> None:
        """
        Build the LangGraph StateGraph from registered agents.
        """
        workflow = StateGraph(SwarmState)

        # 0. Initialize MCP Connections and Skills
        try:
            await self.mcp.load_config(settings.MCP_SERVERS_CONFIG_PATH)
            await self.mcp.connect_all()

            await self.skills.load_all()
        except Exception as e:
            logger.error(f"Failed to initialize MCP or Skills: {e}")

        # 0.4 Add Pre-processor Node (Caching & JIT prep)
        workflow.add_node("pre_processor", self._pre_processor_node)

        # 0.5 Add Retrieval Node
        workflow.add_node("retrieval", self._retrieval_node)

        # 1. Add Supervisor Node
        workflow.add_node("supervisor", self._supervisor_node)

        # 1.1 Add Parallel & Consensus Nodes (M4.2.5)
        workflow.add_node("parallel_worker", self._parallel_node)
        workflow.add_node("consensus", self._consensus_node)

        # 2. Add Agent Nodes
        for name, agent_def in self._agents.items():
            workflow.add_node(name, self._create_agent_node(agent_def))

        # 3. Add Reflection Node
        workflow.add_node("reflection", self._reflection_node)

        # 4. Define Edges
        workflow.set_entry_point("pre_processor")
        workflow.add_conditional_edges(
            "pre_processor", lambda state: state["next_step"], {"supervisor": "supervisor", "FINISH": END}
        )
        workflow.add_edge("retrieval", "supervisor")

        # Add Platform Action Node (for UI navigation/modal requests)
        workflow.add_node("platform_action", self._platform_action_node)
        workflow.add_edge("platform_action", END)

        # Supervisor → Agent, Retrieval, Platform Action, or END
        workflow.add_conditional_edges(
            "supervisor",
            lambda state: state["next_step"],
            {
                **{name: name for name in self._agents},
                "retrieval": "retrieval",
                "parallel": "parallel_worker",
                "FINISH": END,
                "REFLECTION": "reflection",
                "PLATFORM_ACTION": "platform_action",
            },
        )

        # All agents → Decision Node (Flexible Reflection)
        # Instead of going straight to reflection, we go to a decision node
        # to see if reflection is even necessary.
        workflow.add_node("reflection_decision", self._reflection_decision_node)
        for name in self._agents:
            workflow.add_edge(name, "reflection_decision")

        # Reflection Decision → Reflection or END/Supervisor
        workflow.add_conditional_edges(
            "reflection_decision",
            lambda state: state["next_step"],
            {"REFLECTION": "reflection", "FINISH": END, "supervisor": "supervisor"}
        )

        # Reflection → Supervisor or END
        workflow.add_conditional_edges(
            "reflection", self._route_after_reflection, {"supervisor": "supervisor", "FINISH": END}
        )

        # Consensus → Reflection Decision
        workflow.add_edge("consensus", "reflection_decision")
        workflow.add_edge("parallel_worker", "consensus") # Default path from parallel if not routed elsewhere

        # 5. Compile with Persistent Checkpointer (P1 Resilience)
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            import sqlite3
            conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            logger.info(f"🕸️ Swarm Graph compiled with Persistent SqliteSaver: {settings.CHECKPOINT_DB_PATH}")
        except Exception as e:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
            logger.warning(f"⚠️ Persistence init failed, falling back to MemorySaver: {e}")

        self._graph = workflow.compile(checkpointer=checkpointer)

    # ============================================================
    #  Supervisor Node — uses PromptEngine
    # ============================================================

    async def _pre_processor_node(self, state: SwarmState) -> dict:
        """Entry node for caching, JIT context checks, Query Enrichment, and A/B assignment."""
        import random
        messages = state.get("messages", [])
        original_query = state.get("original_query", "")

        # --- 1. Semantic Cache Lookup (Architecture Layer 5 Middleware) ---
        cached = await CacheService.get_cached_response(original_query)
        if cached:
            logger.info(f"⚡ [Phase 4] Semantic Cache Hit: {original_query[:50]}...")
            return {
                "messages": [AIMessage(content=cached["content"])],
                "agent_outputs": {"cache": cached["content"]},
                "next_step": "FINISH",
            }

        # --- 2. A/B Execution Variant Assignment (GOV-EXP-001) ---
        # Only assign if not already set (first turn of conversation)
        execution_variant = state.get("execution_variant") or ""
        if not execution_variant:
            execution_variant = "react" if random.random() < 0.5 else "monolithic"
            logger.info(f"🧪 [A/B] Assigned execution_variant='{execution_variant}' for this session")

        # --- 3. Query Enrichment: Pronoun Resolution & Ambiguity Fix (TASK-RAG-002) ---
        query_to_enrich = original_query
        pronouns = ["it", "that", "this", "he", "she", "they", "them", "它", "这个", "那个", "之前"]
        is_ambiguous = len(query_to_enrich) < 15 or any(p in query_to_enrich.lower() for p in pronouns)

        if is_ambiguous and len(messages) > 1:
            try:
                llm = self.router.get_model(ModelTier.SIMPLE)
                history = "\n".join([f"{m.type}: {m.content[:100]}" for m in messages[-5:-1]])

                enrich_prompt = f"""
                You are a dialogue context analyzer.
                Based on the dialogue history, resolve any pronouns or ambiguity in the Latest User Query to make it a standalone, clear search query.
                
                Dialogue History:
                {history}
                
                Latest User Query: {query_to_enrich}
                
                Standalone Enriched Query (return ONLY the query):
                """

                resp = await llm.ainvoke([HumanMessage(content=enrich_prompt)])
                enriched = resp.content.strip().strip('"')

                if enriched and enriched != query_to_enrich:
                    logger.info(f"🧬 [Query Enrichment] '{query_to_enrich}' -> '{enriched}'")
                    return {
                        "next_step": "supervisor",
                        "original_query": enriched,
                        "execution_variant": execution_variant,
                    }
            except Exception as e:
                logger.error(f"⚠️ Query Enrichment failed: {e}")

        # --- 4. Adaptive Reasoning Budget Scoring (M4.2.8) ---
        complexity_score = 0
        heavy_tasks = ["analyze", "compare", "verify", "audit", "对比", "分析", "审计", "验证"]
        if len(original_query) > 50: complexity_score += 3
        if any(w in original_query.lower() for w in heavy_tasks): complexity_score += 4

        reasoning_budget = 4 if complexity_score < 4 else 8
        logger.info(f"🧠 [Adaptive Budget] Query Complexity={complexity_score} -> Budget={reasoning_budget}")

        return {
            "next_step": "supervisor",
            "execution_variant": execution_variant,
            "reasoning_budget": reasoning_budget
        }

    async def _supervisor_node(self, state: SwarmState) -> dict:
        """
        [溯源]: 项目架构核心 / REQ-Orchestrator
        [设计决策]:
        Supervisor node — 意图识别与路由节点。
        在此节点中，我们没有完全依赖 LLM 来做路由，而是前置了一个【关键字硬编码快速判断（Fast Path）】。
        这是为了极大降低平台操作（如页面跳转、弹窗提示）的响应延迟，避免 RAG 幻觉。

        [🛡️ AI-LOCKED (AI 修改禁区)]:
        绝对不要把这里的 Fast Path 逻辑给删掉，也不要强行用 LLM覆盖这个兜底逻辑。如果需要新增快速匹配命令，请在 `PLATFORM_INTENTS` 数组中追加。
        """
        # --- Context Compaction (P2: LLM Summarization) ---
        state["messages"] = await self._compact_messages(
            state["messages"],
            user_id=state.get("user_id"),
            conversation_id=state.get("conversation_id"),
            pinned_messages=state.get("pinned_messages")
        )

        messages = state["messages"]
        user_query = str(state.get("original_query", "") or (messages[-1].content if messages else ""))

        # === Fast Path: JIT Route Cache (GOV-004) ===
        cached_route = await CacheService.get_cached_route(user_query)
        if cached_route:
            logger.info(f"⚡ [JIT Route Cache] Hit: {user_query[:30]} -> {cached_route}")
            return {
                "next_step": cached_route,
                "uncertainty_level": 0.0,
                "current_task": "Restored from route cache.",
                "last_node_id": "supervisor_cache",
                "thought_log": f"⚡ JIT 缓存命中: 直接跳转到 {cached_route}",
            }

        # === Fast Path: Keyword-based Platform Action Detection ===
        # Intercept navigation intents BEFORE calling LLM for routing.
        # This is deterministic, cheap, and prevents hallucination in RAG agents.
        PLATFORM_INTENTS = [
            (
                ["创建知识库", "新建知识库", "create knowledge base", "create kb"],
                "open_modal:create_kb",
                '好的，现在为您打开**创建知识库**向导。\n[ACTION: {"type": "open_modal", "target": "create_kb", "label": "立刻创建", "variant": "primary"}]',
            ),
            (
                ["上传文档", "上传文件", "upload document", "upload file"],
                "navigate:/knowledge",
                '我来帮您跳转到**知识库管理**页面，在那里您可以上传文档。\n[ACTION: {"type": "navigate", "target": "/knowledge", "label": "去上传文档", "variant": "primary"}]',
            ),
            (
                ["去评测", "运行评测", "run evaluation", "跳转到评测"],
                "navigate:/evaluation",
                '好的，现在为您跳转到**评测中心**。\n[ACTION: {"type": "navigate", "target": "/evaluation", "label": "前往评测中心", "variant": "primary"}]',
            ),
        ]

        for keywords, action, reply_template in PLATFORM_INTENTS:
            if any(kw.lower() in user_query.lower() for kw in keywords):
                logger.info(f"[Supervisor Fast Path] Detected platform intent: {action}")
                return {
                    "next_step": "PLATFORM_ACTION",
                    "uncertainty_level": 0.0,
                    "current_task": action,
                    "context_data": reply_template,  # Pass template to the action node
                    "last_node_id": "supervisor_fast",
                    "thought_log": f"⚡ 快速匹配: 检测到平台操作指令 '{keywords[0]}'",
                }

        # === Mid Path: Vector-based Agent Routing (5.3 VectorAgentRouter, Tier 1) ===
        # Faster than LLM but richer than keyword matching. Falls through to LLM if confidence < threshold.
        vector_route = await vector_agent_router.route(user_query)
        if vector_route and vector_route in self._agents:
            logger.info(f"⚡ [Vector Router] Matched → '{vector_route}'")
            return {
                "next_step": vector_route,
                "uncertainty_level": 0.25,
                "current_task": f"向量路由 → {vector_route}",
                "last_node_id": "supervisor_vector",
                "thought_log": f"⚡ 向量路由命中: 直接分配给 {vector_route}",
            }

        # === Regular Path: Use LLM for routing ===
        # Build agent info for PromptEngine
        agents_info = [{"name": name, "description": a.description} for name, a in self._agents.items()]
        # Add retrieval as a pseudo-agent for Adaptive RAG
        agents_info.append(
            {
                "name": "retrieval",
                "description": "Knowledge Retrieval System. Route here if you need more context or factual information from the internal knowledge bases before answering.",
            }
        )

        # Build prompt via PromptEngine (Layer 1 + 2 + 3)
        system_prompt = self.prompt_engine.build_supervisor_prompt(
            agents=agents_info,
            rag_context=state.get("context_data", ""),
            memory_context="", # Supervisor doesn't strictly need memory snippets yet
            language=state.get("language", "zh-CN"),
        )

        # --- Speculative Retrieval (Phase 6: Parallel Intent & Recall) ---
        # We start retrieval in parallel with the Router LLM.
        # This saves ~300-800ms of graph-hop latency and DB lookup time.
        retrieval_task = None
        # Always trigger if kb_ids is provided, or if query looks like research
        if state.get("kb_ids") or any(
            kw in user_query.lower()
            for kw in ["search", "find", "what", "how", "query", "搜索", "查询", "是啥", "什么"]
        ):
            logger.info("⚡ [Phase 6] Starting speculative retrieval task...")
            retrieval_task = asyncio.create_task(self._do_retrieval_work(state))

        # Setup LLM and Prompt
        # --- P1: Routing Watchdog (Tier Escalation) ---
        tier = ModelTier.SIMPLE
        if state.get("force_reasoning_tier"):
            logger.warning("🦅 [Routing Watchdog] Escalating Supervisor to REASONING tier due to prior conflict.")
            tier = ModelTier.REASONING

        llm = self.router.get_model(tier)
        final_prompt = [SystemMessage(content=system_prompt), *messages]


        # Parallel: Router LLM + Speculative Retrieval (M6.1.1)
        aws = [llm.ainvoke(final_prompt)]
        if retrieval_task:
            aws.append(retrieval_task)

        res_list = await asyncio.gather(*aws, return_exceptions=True)

        response = res_list[0]
        if isinstance(response, Exception):
            logger.error(f"Router LLM failed: {response}")
            return {"next_step": "FINISH", "status_update": "❌ 路由节点故障"}

        # Now we can safely access .content
        content = getattr(response, "content", "")

        pre_retrieval_result = None
        if retrieval_task and len(res_list) > 1:
            val = res_list[1]
            if not isinstance(val, Exception):
                pre_retrieval_result = val

        if isinstance(response, Exception):
            logger.error(f"Router LLM failed: {response}")
            return {"next_step": "FINISH", "status_update": "❌ 路由节点故障"}

        content = response.content
        # Parse JSON
        decision = self._parse_routing_decision(content)

        logger.info(f"👨‍✈️ Supervisor: {decision.next_agent} (uncertainty={decision.uncertainty:.2f})")

        next_step = decision.next_agent
        updates = {
            "next_step": next_step,
            "current_task": decision.reasoning,
        }

        # --- Phase 6: Speculative Pickup ---
        # If we already did retrieval and the supervisor says go to retrieval,
        # we can just merge the result HERE and skip the retrieval node's next-tick latency.
        if decision.next_agent == "retrieval" and pre_retrieval_result:
            if pre_retrieval_result.get("retrieved_docs"):
                logger.info("⚡ [Phase 6] Speculative Retrieval Hit! Merging new docs.")
                # Merge into updates but keep existing context if it was already there
                existing_context = state.get("context_data", "")
                if existing_context and pre_retrieval_result["context_data"]:
                    updates["context_data"] = f"{existing_context}\n\n{pre_retrieval_result['context_data']}"
                else:
                    updates.update(pre_retrieval_result)
            else:
                logger.debug("🔍 [Phase 6] Speculative Retrieval returned no results. Skipping merge.")
            # Since we merged it, we can tell LangGraph to go back to supervisor
            # or directly to an agent? No, keep the graph flow, but the retrieval node
            # will now see the context is already there and be a no-op.
        # --- Phase 5: Task Scaffolding (Architecture Layer 2 Persistence) ---
        # If the LLM proposed a multi-step plan, persist it as a shared TODO list
        if decision.planned_steps:
            from app.models.agents import TodoItem, TodoStatus

            for step in decision.planned_steps:
                await self.memory.add_todo(
                    TodoItem(
                        title=step,
                        status=TodoStatus.PENDING,
                        created_by="supervisor",
                        assigned_to=next_step,
                        source_conversation_id=state.get("conversation_id"),
                    )
                )
            logger.info(f"📝 [Phase 5] Supervisor persisted plan with {len(decision.planned_steps)} steps to Memory.")

        logger.info(f"🗺️ Supervisor planned {len(decision.planned_steps)} steps")

        import uuid

        node_id = f"supervisor_{uuid.uuid4().hex[:6]}"

        # --- P1: Smart Cache & Short-Circuit ---
        # If uncertainty is extremely low AND next_step is FINISH, avoid any morehops.
        if decision.uncertainty < 0.1 and next_step == "FINISH":
             logger.info("⚡ [Supervisor] High confidence end. Short-circuiting.")
             return {"next_step": "FINISH", "messages": [AIMessage(content="Task completed with high confidence.")]}

        return {
            "next_step": next_step,
            "uncertainty_level": decision.uncertainty,
            "current_task": decision.task_refinement,
            "last_node_id": node_id,
            "status_update": (
                f"🗺️ Supervisor planned {len(decision.planned_steps)} steps" if decision.planned_steps else None
            ),
            "thought_log": f"👨‍✈️ 决策路径: {decision.reasoning}",
            "force_reasoning_tier": False, # Reset after use
            "parallel_agents": decision.parallel_agents, # [M4.2.5]
        }

    # ============================================================
    #  Parallel & Consensus Logic (M4.2.5)
    # ============================================================

    async def _parallel_node(self, state: SwarmState) -> dict:
        """
        [M4.2.5] 并行协作节点。
        根据 Supervisor 的决策，并行调用多个专家 Agent，并将结果合并至 agent_outputs。
        """
        agents_to_invoke = state.get("parallel_agents", [])
        if not agents_to_invoke:
            return {"next_step": "FINISH", "status_update": "⚠️ 并行节点未分配任务"}

        logger.info(f"⚡ [M4.2.5] Parallel execution triggered for: {agents_to_invoke}")

        # 1. Prepare tasks for all agents
        tasks = []
        for agent_name in agents_to_invoke:
            agent_def = self._agents.get(agent_name)
            if agent_def:
                # Use the existing factory-built node function
                node_func = self._create_agent_node(agent_def)
                tasks.append(node_func(state))
            else:
                logger.warning(f"Unknown agent in parallel list: {agent_name}")

        if not tasks:
            return {"next_step": "supervisor"}

        # 2. Fan-out execution (Parallel)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. Fan-in results
        merged_outputs = state.get("agent_outputs", {}).copy()
        merged_msgs = []

        for i, res in enumerate(results):
            agent_name = agents_to_invoke[i]
            if isinstance(res, Exception):
                logger.error(f"❌ Parallel Agent {agent_name} failed: {res}")
                merged_outputs[agent_name] = f"Error: {res}"
            else:
                merged_outputs.update(res.get("agent_outputs", {}))
                merged_msgs.extend(res.get("messages", []))

        logger.info(f"⚡ Parallel execution completed for {len(tasks)} agents.")

        # Determine next step: if more than 1 agent was used, go to CONSENSUS
        next_step = "consensus" if len(agents_to_invoke) > 1 else "reflection_decision"

        return {
            "agent_outputs": merged_outputs,
            "messages": merged_msgs,
            "next_step": next_step,
            "status_update": f"⚡ 并行协作完成：{', '.join(agents_to_invoke)}",
            "thought_log": f"⚡ 并行执行器聚合了 {len(agents_to_invoke)} 个智体的响应",
        }

    async def _consensus_node(self, state: SwarmState) -> dict:
        """
        [M4.2.5] 共识合成节点。
        当多个 Agent 观点不一致时，使用高阶 LLM 进行辩论总结与共识达成。
        """
        agent_outputs = state.get("agent_outputs", {})
        original_query = state.get("original_query", "")
        task = state.get("current_task", "")

        # Format the debate for the LLM
        debate_buffer = []
        for name, output in agent_outputs.items():
            # Only include recent outputs from the current parallel run
            if name in state.get("parallel_agents", []):
                debate_buffer.append(f"【{name} 的观点】:\n{output}")

        debate_text = "\n\n".join(debate_buffer)

        system_prompt = f"""
        You are the Swarm Consensus Synthesizer.
        Multiple specialist agents have worked on the following task in parallel, and they may have different perspectives or conflicting results.
        Your goal is to synthesize their outputs into a single, high-quality, and coherent answer that resolves any conflicts.
        
        Original User Query: {original_query}
        Current Sub-task: {task}
        
        --- AGENT DEBATE ---
        {debate_text}
        --- END DEBATE ---
        
        Synthesis Guidelines:
        1. If agents agree, reinforce the consensus.
        2. If agents conflict, analyze the reasoning of each and choose the most evidence-backed or logical one.
        3. Factual truth from RAG agents usually outweighs creative suggestions from Code/Web agents.
        4. Maintain a unified tone for the final response.
        
        Final Synthesized Answer (Markdown):
        """

        llm = self.router.get_model(ModelTier.REASONING) # Escalated tier for consensus
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])

        logger.info("⚖️ Consensus reached through agentic debate.")

        return {
            "messages": [AIMessage(content=response.content)],
            "agent_outputs": {"consensus": str(response.content)},
            "next_step": "reflection_decision",
            "status_update": "⚖️ 多智体共识合成完成",
            "thought_log": "⚖️ 已综合多个智体的独立见解，解决潜在冲突并形成最终一致性结论",
        }


    # ============================================================
    #  Agent Node — uses PromptEngine
    # ============================================================

    # ============================================================
    #  ReAct Distributed Thinking Loop (GOV-EXP-001)
    # ============================================================


    def _create_agent_node(self, agent_def: AgentDefinition):
        """Factory for agent execution nodes with tool calling capability."""

        async def agent_node(state: SwarmState) -> dict:
            # --- Scoped State Filtering (M5.1.1) ---
            scoped_state = ScopedStateView.filter(state, agent_def.name)

            task = scoped_state.get("current_task", "")
            conv_id = scoped_state.get("conversation_id", "")
            logger.info(f"🤖 Agent [{agent_def.name}] working on: {task[:80]}")

            # --- Phase 5: Task Progress Tracking (Persistent) ---
            # Mark assigned pending tasks as In Progress
            from app.models.agents import TodoStatus

            if conv_id:
                todos = await self.memory.get_todos(status=TodoStatus.PENDING)
                for todo in todos:
                    if todo.source_conversation_id == conv_id and todo.assigned_to == agent_def.name:
                        await self.memory.update_todo(todo.id, status=TodoStatus.IN_PROGRESS)
                        logger.debug(f"📉 Task '{todo.title}' marked as IN_PROGRESS")

            # 1. Prepare Tools
            # Combine native tools with agent-specific tools, and MCP tools
            available_tools = list(agent_def.tools)
            if agent_def.name != "supervisor":
                # 1.1 Add mandatory native tools (inspired by CC's always_load)
                mandatory_tools = [t for t in NATIVE_TOOLS if getattr(t, "_hive_meta", None) and t._hive_meta.always_load]
                available_tools.extend(mandatory_tools)

                # 1.2 Adaptive Discovery: Only load relevant deferred tools for the current task
                # This prevents context explosion and improves model focus.
                if task:
                    logger.debug(f"🔍 [Tool Discovery] Filtering specialized tools for task: {task[:50]}...")

                    # 1.2.1 Search in native tools that are NOT always loaded (Deferred Tools)
                    # Use semantic search if available (P2 Upgrade)
                    await self.tool_index.initialize_embeddings() # Ensure ready
                    available_tools.extend(await self.tool_index.asearch(task, limit=5))

                    # 1.2.2 Discover relevant MCP tools (P2 semantic logic)
                    mcp_tools = await self.mcp.discover_tools(task, limit=10)
                    available_tools.extend(mcp_tools)

                    # 1.2.3 Discover relevant Skills
                    discovered_skills = self.skills.discover(task, limit=5)
                    for skill in discovered_skills:
                        available_tools.extend(skill.tools)

                    # 1.2.4 Add agentic search tools (usually needed for research)
                    if any(kw in task.lower() for kw in ["search", "find", "who", "what", "how", "搜索", "查找"]):
                        available_tools.extend(SEARCH_TOOLS)

                else:
                    # Fallback for empty task: load a minimal set
                    logger.warning(f"⚠️ Empty task for agent {agent_def.name}, loading minimal tools")
                    available_tools.extend(SEARCH_TOOLS[:2])

            # --- Tool Auditing (Phase 3) ---
            from app.services.security.sanitizer import SecuritySanitizer

            # 2. Prepare Memory Context (ARM-P1-3)
            memory_context = ""
            user_id = state.get("user_id")
            if user_id:
                from app.services.memory.memory_service import MemoryService

                mem_svc = MemoryService(user_id=user_id)
                # If we have role info in auth_context, use it
                role_id = state["auth_context"].role if state.get("auth_context") else None
                memory_context = await mem_svc.get_context(query=task, role_id=role_id)

            # 🧬 [GOV-004] Dynamic Context Anchoring — Inject structural markers for long-context
            # to help combat 'Lost in the Middle' problem.
            rag_context = state.get("context_data", "")
            prompt_variant = state.get("prompt_variant", "default")

            # --- Token Governance (P0 Hardening) ---
            rag_budget = int(settings.CONTEXT_WINDOW_LIMIT * settings.BUDGET_RAG_RATIO)
            mem_budget = int(settings.CONTEXT_WINDOW_LIMIT * settings.BUDGET_MEMORY_RATIO)

            rag_context = TokenService.truncate_to_budget(rag_context, rag_budget)
            memory_context = TokenService.truncate_to_budget(memory_context, mem_budget)

            if len(rag_context) > 10000 or prompt_variant == "head_tail_v1":
                from app.services.agents.prompt_fixer import VirtualSegmenter
                # Auto-upgrade to head_tail_v1 if context is massive (>5000 tokens)
                if len(rag_context) > 20000 and prompt_variant == "default":
                    prompt_variant = "head_tail_v1"
                    logger.info("🧬 [Dynamic Prompt] Autograded to 'head_tail_v1' due to massive context size.")

                # Apply structural markers (Virtual Segmenting)
                rag_context = VirtualSegmenter.inject_markers(rag_context)

            system_prompt = self.prompt_engine.build_agent_prompt(
                agent_name=agent_def.name,
                task=task,
                rag_context=rag_context,
                memory_context=memory_context,
                tools_available=[t.name for t in available_tools if hasattr(t, "name")],
                prompt_variant=prompt_variant,
                language=state.get("language", "zh-CN"),
            )

            # 3. Get the appropriate LLM and bind tools
            llm = self._get_llm_for_agent(agent_def)
            if available_tools:
                llm = llm.bind_tools(available_tools)

            # --- Context Compaction (P2: LLM Summarization) ---
            state["messages"] = await self._compact_messages(
                state["messages"],
                user_id=state.get("user_id"),
                conversation_id=state.get("conversation_id"),
                pinned_messages=state.get("pinned_messages")
            )

            # 4. Invoke Engine — OPT-2 Streaming and Broadcasting
            execution_variant = state.get("execution_variant", "monolithic")
            user_id = state.get("user_id", "")

            logger.info(f"🧪 [OPT-2] Agent [{agent_def.name}] launching engine (variant={execution_variant})")

            updates = await self.engine.stream_and_broadcast(
                conversation_id=conv_id,
                user_id=user_id,
                agent_def=agent_def,
                llm=llm,
                available_tools=available_tools,
                system_prompt=system_prompt,
                state=scoped_state,  # Use scoped state for engine loop
            )

            # Extract results from engine update dict
            session_thinking_times = updates.get("thinking_time_ms", [])
            session_tool_times = updates.get("tool_time_ms", [])
            new_messages = updates.get("messages", [])
            final_content = updates.get("agent_outputs", {}).get(agent_def.name, "")

            total_think_ms = sum(session_thinking_times)
            logger.info(f"⏱️ [OPT-2] Agent [{agent_def.name}] finished stream. total_think={total_think_ms:.0f}ms")

            # We want the content of the most recent AIMessage for agent_outputs
            final_ai_msg = next((m for m in reversed(current_messages) if isinstance(m, AIMessage)), None)
            final_content = final_ai_msg.content if final_ai_msg else "Task completed with tools."

            # --- Output Sanitization (Phase 3) ---
            final_content = SecuritySanitizer.mask_text(str(final_content))

            new_msgs_count = len(current_messages) - (1 + len(state["messages"]))
            new_messages = current_messages[-new_msgs_count:] if new_msgs_count > 0 else []

            import uuid

            node_id = f"{agent_def.name}_{uuid.uuid4().hex[:6]}"

            # Record node linkage for frontend DAG trace
            if state.get("last_node_id"):
                # We could link the supervisor to this node, but we'll let frontend link it
                # or just use sequential linking if we want.
                pass

            # --- Phase 5: Task Progress Completion ---
            if conv_id:
                # Mark In Progress tasks as Completed
                todos = await self.memory.get_todos(status=TodoStatus.IN_PROGRESS)
                for todo in todos:
                    if todo.source_conversation_id == conv_id and todo.assigned_to == agent_def.name:
                        await self.memory.update_todo(todo.id, status=TodoStatus.COMPLETED)
                        logger.info(f"✅ Task '{todo.title}' marked as COMPLETED by {agent_def.name}")

            # --- A/B Telemetry: persist to ab_tracker ---
            try:
                from app.services.evaluation.ab_tracker import ab_tracker
                ab_tracker.record(
                    conversation_id=conv_id or "unknown",
                    agent_name=agent_def.name,
                    execution_variant=execution_variant,
                    thinking_times_ms=session_thinking_times,
                )
            except Exception as _e:
                logger.debug(f"[AB Tracker] record failed (non-critical): {_e}")

            return {
                "messages": new_messages,
                "agent_outputs": {agent_def.name: str(final_content)},
                "last_node_id": node_id,
                "thinking_time_ms": session_thinking_times,
                "tool_time_ms": session_tool_times,
                "status_update": f"✅ {agent_def.name} finished.",
                "thought_log": (
                    f"⏱️ [{execution_variant}] Think={sum(session_thinking_times):.0f}ms | "
                    f"Tool={sum(session_tool_times):.0f}ms"
                ),
            }

        return agent_node

    async def _execute_tool(
        self,
        tool_call: dict,
        available_tools: list[BaseTool],
        agent_name: str,
        state: SwarmState
    ) -> tuple[str, float]:
        """
        CC-inspired centralized tool execution.
        Handles:
        1. Tool Discovery
        2. Security Auditing (Fail-closed)
        3. Sandbox Execution
        4. Telemetry collection
        """
        import time as _time

        from app.services.security.sanitizer import ToolAuditor

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # Inject agent context if tool supports it
        if "agent_name" in tool_args:
            tool_args["agent_name"] = agent_name

        tool_obj = next((t for t in available_tools if getattr(t, "name", "") == tool_name), None)
        if not tool_obj:
            return f"Error: Tool '{tool_name}' not found.", 0.0

        meta = getattr(tool_obj, "_hive_meta", None)
        t_start = _time.monotonic()

        try:
            # 🛡️ Process CC-inspired 4-Layer Security Chain (OPT-4)
            auth = state.get("auth_context")
            audit = ToolAuditor.audit_chain(tool_name, tool_args, meta=meta, auth=auth)

            if not audit.is_safe:
                logger.warning(f"🚫 [Security Chain] Tool '{tool_name}' blocked. Reason: {audit.message}")
                return f"Error: Tool call blocked by security policy ({audit.error_code}). {audit.message}", 0.0

            if audit.requires_approval:
                # OPT-4 Layer 4: Consent flow
                # In this phase, we mock the consent or return a blocker.
                # True HITL would require yielding an 'approval_required' event and pausing.
                logger.info(f"⚖️ [Consent Required] Blocking {tool_name} for manual review.")
                return f"ACTION_REQUIRED: Tool '{tool_name}' is destructive and requires manual confirmation.", 0.0

            # 🛠️ Execute (Branch by architecture)
            if tool_name == "programmatic_execute":
                logger.info(f"⚡ [Sandbox] Entering Tool Sandbox for Agent: {agent_name}")
                sandbox = ToolSandbox(available_tools=available_tools)
                result = await sandbox.run_script(tool_args.get("script", ""))
            else:
                result = await tool_obj.ainvoke(tool_args)

            duration = (_time.monotonic() - t_start) * 1000
            return str(result), duration

        except Exception as e:
            logger.error(f"❌ Tool Execution Failed [{tool_name}]: {e}")
            return f"Tool Error: {e!s}", (_time.monotonic() - t_start) * 1000

    async def _platform_action_node(self, state: SwarmState) -> dict:

        logger.info("[PlatformAction] Responding with direct action reply")

        return {
            "messages": [AIMessage(content=reply)],
            "agent_outputs": {"platform_action": reply},
        }

    async def _reflection_decision_node(self, state: SwarmState) -> dict:
        """
        Decision node to determine if explicit reflection is required.
        
        Logic:
        1. If it's a simple informational task with low uncertainty, skip reflection.
        2. If hard rules (sanitizer) are already tripped in the agent output, force reflection.
        3. If it's a critical write operation, always reflect.
        """
        uncertainty = state.get("uncertainty_level", 0.5)
        last_node = state.get("last_node_id", "")
        agent_outputs = state.get("agent_outputs", {})
        last_output = list(agent_outputs.values())[-1] if agent_outputs else ""

        # 1. Hard Rule: Security check (Cheap/Local)
        from app.services.security.sanitizer import SecuritySanitizer
        if SecuritySanitizer.contains_sensitive_data(str(last_output)):
            logger.warning("🛡️ [Reflection Decision] Sensitive data detected. Forcing Reflection.")
            return {"next_step": "REFLECTION"}

        # 2. Heuristic: Confidence & Node Type
        # If uncertainty is low (< 0.3) and it's not a complex code task, skip.
        is_complex = any(agent in last_node for agent in ["code", "sql", "orchestrator"])

        if uncertainty < 0.3 and not is_complex:
            logger.info(f"⚡ [Reflection Decision] High confidence ({uncertainty:.2f}) & Low complexity. Skipping Reflection.")
            return {"next_step": "FINISH"}

        # 3. Default: Fallback to Reflection for safety
        logger.info(f"🪞 [Reflection Decision] Proceeding to Reflection (Uncertainty: {uncertainty:.2f}).")
        return {"next_step": "REFLECTION"}

    # ============================================================
    #  Reflection Node — uses PromptEngine + LLM
    # ============================================================

    async def _reflection_node(self, state: SwarmState) -> dict:
        """
        Reflection node — evaluates agent output quality using LLM.

        2.1H Hybrid Reflection: Hard-rule validators run FIRST (cheap, deterministic).
        Only if all hard rules pass does the expensive LLM evaluation run.

        Hard rules checked:
          1. Empty / too-short response (< 5 meaningful chars)
          2. Security: prohibited injection patterns (OWASP Top 10 injection defense)
          3. JSON schema integrity (when agent was asked to output structured JSON)
        """
        last_message = state["messages"][-1]
        reflection_count = state.get("reflection_count", 0) + 1

        logger.info(f"🪞 Reflection #{reflection_count}...")

        # Quick circuit breaker: skip LLM evaluation if we've reflected too much
        if reflection_count > 3:
            logger.warning("🪞 Too many reflections, forcing FINISH")
            return {
                "reflection_count": reflection_count,
                "next_step": "FINISH",
            }

        # ── 2.1H: Hybrid Reflection — Tier 0: Hard-Rule Validators ───────────
        content = getattr(last_message, "content", "") or ""
        hard_violations: list[str] = []

        # Rule 1: Empty / too-short response
        if len(content.strip()) < 5:
            hard_violations.append("empty_response")

        # Rule 2: Security — detect prompt-injection and dangerous code patterns
        _PROHIBITED_PATTERNS = [
            "<script",
            "javascript:",
            "DROP TABLE",
            "sudo rm -rf",
            "ignore previous instructions",
            "ignore all instructions",
            "system: override",
        ]
        for pattern in _PROHIBITED_PATTERNS:
            if pattern.lower() in content.lower():
                hard_violations.append(f"prohibited_content:{pattern[:24]}")
                break

        # Rule 3: JSON schema check — when the agent explicitly requested JSON output
        if state.get("expect_json_output"):
            try:
                json.loads(content)
            except (json.JSONDecodeError, ValueError):
                hard_violations.append("invalid_json_output")

        if hard_violations:
            logger.warning(f"🔍 [Hybrid Reflection] Hard-rule violations detected: {hard_violations}")
            return {
                "reflection_count": reflection_count,
                "next_step": "supervisor",  # Force retry
                "hard_rule_violations": hard_violations,
                "thought_log": f"⚠️ Hard-rule validation failed: {hard_violations}. Routing back to supervisor.",
            }

        logger.debug("🔍 [Hybrid Reflection] Hard rules passed — proceeding to LLM evaluation.")
        # ── End of Hard-Rule Validators ───────────────────────────────────────

        # Determine which agent produced the last output
        agent_outputs = state.get("agent_outputs", {})
        last_agent_name = list(agent_outputs.keys())[-1] if agent_outputs else "unknown"

        # Build reflection prompt via PromptEngine
        self.prompt_engine.build_reflection_prompt(
            user_query=state.get("original_query", ""),
            agent_name=last_agent_name,
            agent_response=last_message.content[:1500],  # Truncate to save tokens
            task_description=state.get("current_task", ""),
            language=state.get("language", "zh-CN"),
        )

        # Invoke LLM for quality check (using BALANCED or FAST)
        # --- Advanced Multi-Grader Evaluation (Phase 3) ---
        evaluator = MultiGraderEval()

        # --- Routing Watchdog: Truth Alignment Integration (P1) ---
        # If the context data contains a conflict warning, we explicitly tell the evaluator to look for it.
        context_data = state.get("context_data", "")
        if "⚠️ CONFLICT" in context_data:
            logger.warning("🚨 [Routing Watchdog] Factual conflict detected in retrieval. Triggering enhanced scrutiny.")
            # We don't change the evaluation data, but the MultiGrader will catch it via the 'consistency' criteria

        eval_result = await evaluator.evaluate(
            query=state.get("original_query", ""), response=last_message.content, context=context_data
        )

        # 🧬 [Dynamic Feedback Loop] Context Overload Detection
        # If the evaluator says FAIL/REVISE, and we suspect 'Lost in Middle', we switch prompt variant for the retry.
        prompt_variant = state.get("prompt_variant", "default")
        suggested_variant = prompt_variant
        if eval_result.verdict in ["FAIL", "REVISE"]:
            from app.services.agents.prompt_fixer import VirtualSegmenter
            failure_cause = VirtualSegmenter.detect_failure_cause(
                query=state.get("original_query", ""),
                response=last_message.content,
                context=context_data
            )
            if failure_cause == "lost_in_middle_likely" and prompt_variant == "default":
                logger.info("🧬 [Dynamic Detection] 'Lost in Middle' detected. Suggested strategy: 'head_tail_v1'")
                suggested_variant = "head_tail_v1"

        # Decide next step based on composite score
        next_step = "FINISH" if eval_result.verdict in ["PASS", "EXCELLENT"] else "supervisor"

        if should_escalate:
             # We can't change the model here directly, but we can set a flag in the state
             # that the supervisor/router will pick up in the next loop.
             # For now, we use node metadata or state updates.
             pass

        # --- Automatic Semantic Caching (Phase 4 / GOV-004) ---
        if eval_result.verdict in ["PASS", "EXCELLENT"] and eval_result.composite_score >= 0.8:
            from app.services.cache_service import CacheService

            # 1. Cache the Answer
            self._track_task(
                CacheService.set_cached_response(
                    query=state.get("original_query", ""),
                    response=last_message.content,
                    metadata={"agent": last_agent_name, "score": eval_result.composite_score},
                )
            )

            # 2. Cache the Route (GOV-004 JIT)
            # Only cache if it's not a generic 'supervisor' route
            if last_agent_name not in ["supervisor", "reflection", "pre_processor"]:
                self._track_task(
                    CacheService.set_cached_route(
                        query=state.get("original_query", ""),
                        target=last_agent_name
                    )
                )

            logger.info("💾 [GOV-004] Queued response and route for cache.")


        import uuid

        node_id = f"reflection_{uuid.uuid4().hex[:6]}"

        # Tier Escalation Logic (P1)
        consistency_score = next((o.score for o in eval_result.opinions if o.aspect == "consistency"), 1.0)
        should_escalate = eval_result.verdict == "ESCALATE" or consistency_score < 0.4

        # --- A/B Telemetry: back-fill quality score for the last agent's record ---
        try:
            from app.services.evaluation.ab_tracker import ab_tracker
            # Update most recent record that matches this conversation
            conv_id = state.get("conversation_id", "unknown")
            if ab_tracker._records:
                for rec in reversed(ab_tracker._records):
                    if rec.conversation_id == conv_id and rec.quality_score < 0:
                        rec.quality_score = eval_result.composite_score
                        logger.debug(
                            f"📊 [AB Tracker] Back-filled quality_score={eval_result.composite_score:.2f} "
                            f"for {rec.execution_variant}/{rec.agent_name}"
                        )
                        break
        except Exception as _e:
            logger.debug(f"[AB Tracker] quality backfill failed (non-critical): {_e}")

        return {
            "reflection_count": reflection_count,
            "next_step": next_step,
            "last_node_id": node_id,
            "prompt_variant": suggested_variant,
            "force_reasoning_tier": should_escalate,
        }


    def _route_after_reflection(self, state: SwarmState) -> Literal["supervisor", "FINISH"]:
        """Route based on reflection's decision."""
        # Safety limit for loops
        if state.get("reflection_count", 0) > 5:
            return "FINISH"

        next_step = state.get("next_step", "supervisor")
        if next_step == "FINISH":
            return "FINISH"
        return "supervisor"

    # ============================================================
    #  Retrieval Node — uses multi-tier memory
    # ============================================================

    async def _retrieval_node(self, state: SwarmState) -> dict:
        """
        Retrieval node — fetches context from Radar/Graph/Vector tiers.
        If the supervisor already did speculative retrieval, this may be a NO-OP.
        """
        if state.get("context_data"):
            logger.info("🔍 Retrieval node: Context already exists (Speculative Hit). Skipping.")
            return {"status_update": "⚡ 已应用预取检索结果"}

        return await self._do_retrieval_work(state)

    async def _do_retrieval_work(self, state: SwarmState) -> dict:
        """Core retrieval logic shared by node and pre-warmer."""
        query = str(state.get("original_query", ""))

        context_str = ""
        kb_ids = state.get("kb_ids", [])
        retrieval_trace = []
        retrieved_docs = []

        try:
            from app.services.retrieval.pipeline import get_retrieval_service

            if not self._retriever:
                self._retriever = get_retrieval_service()

            if not kb_ids:
                from app.services.retrieval.routing import KnowledgeBaseSelector

                selector = KnowledgeBaseSelector()
                selected_kbs = await selector.select_kbs(query)
                kb_ids = [kb.id for kb in selected_kbs]

            if kb_ids:
                # Optimized Session lookup
                from app.core.database import async_session_factory
                from app.models.chat import User
                from app.models.knowledge import KnowledgeBase
                from app.services.knowledge.kb_service import KnowledgeService

                collection_names = []
                async with async_session_factory() as db_session:
                    user_id = state.get("user_id")

                    # 1. If user context exists, get accessible KBs to filter
                    accessible_kbs = None
                    if user_id:
                        user = await db_session.get(User, user_id)
                        if user:
                            svc = KnowledgeService(db_session)
                            accessible_kbs = await svc.get_user_accessible_kbs(user)

                    # 2. Add collection names for allowed KBs
                    for kid in kb_ids:
                        if accessible_kbs is not None and kid not in accessible_kbs:
                            logger.warning(f"Skipping KB {kid} due to missing permissions for user {user_id}")
                            continue

                        kb = await db_session.get(KnowledgeBase, kid)
                        if kb and kb.vector_collection:
                            collection_names.append(kb.vector_collection)

                if collection_names:
                    docs, trace_logs = await self._retriever.run(
                        query=query,
                        collection_names=collection_names,
                        top_k=5,
                        top_n=3,
                        variant=state.get("retrieval_variant", "default"),
                        auth_context=state.get("auth_context"),
                    )

                    retrieval_trace = trace_logs
                    retrieved_docs = [d.dict() for d in docs]

                    if docs:
                        context_str += "--- DEEP CONTEXT (RAG) ---\n"
                        for i, d in enumerate(docs):
                            fname = d.metadata.get("file_name", "Unknown File")
                            pg = d.metadata.get("page", "?")
                            context_str += f"[{i + 1}] {fname} (p.{pg}):\n{d.page_content}\n\n"
        except Exception as e:
            logger.warning(f"Retrieval work failed: {e}")

        import uuid

        node_id = f"retrieval_{uuid.uuid4().hex[:6]}"
        return {
            "context_data": context_str,
            "last_node_id": node_id,
            "retrieval_trace": retrieval_trace,
            "retrieved_docs": retrieved_docs,
        }

    # ============================================================
    #  Context Compaction Utilities (2.1H)
    # ============================================================

    # Token budget for swarm chat history (20% of 32K = 6400 tokens).
    _HISTORY_TOKEN_BUDGET: int = 6400
    # Keep the last N turns fully intact, only summarize older history.
    _KEEP_INTACT_TURNS: int = 6

    def _prune_messages(
        self, messages: list[BaseMessage], max_messages: int = 25, char_budget: int = 24000
    ) -> list[BaseMessage]:
        """
        Fast synchronous pruning: count-based + Tool Result Clearing + char budget.
        Called as a cheap guard before entering the async LLM summarization path.
        """
        if not messages:
            return []

        # 1. Message Count Pruning
        if len(messages) > max_messages:
            logger.info(f"🧹 [Phase 6] Pruning by count: {len(messages)} -> {max_messages}")
            system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
            other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
            messages = system_msgs + other_msgs[-(max_messages - len(system_msgs)) :]

        # 2. Tool Result Clearing
        keep_intact_count = self._KEEP_INTACT_TURNS
        head_msgs = messages[:-keep_intact_count] if len(messages) > keep_intact_count else []
        tail_msgs = messages[-keep_intact_count:] if len(messages) > keep_intact_count else messages

        refined_head = []
        for msg in head_msgs:
            if isinstance(msg, ToolMessage) and len(str(msg.content)) > 150:
                summary = f"[Output of {msg.tool_call_id[:8]}... summarized: {len(str(msg.content))} chars truncated]"
                refined_head.append(ToolMessage(tool_call_id=msg.tool_call_id, content=summary))
            else:
                refined_head.append(msg)

        current_messages = refined_head + tail_msgs

        # 3. Total Character Budget Check
        total_chars = sum(len(str(m.content)) for m in current_messages)
        if total_chars > char_budget:
            logger.info(f"⚖️ [Phase 6] Budget exceeded ({total_chars} > {char_budget}). Removing intermediate history.")
            system_msgs = [m for m in current_messages if isinstance(m, SystemMessage)]
            other_msgs = [m for m in current_messages if not isinstance(m, SystemMessage)]

            while other_msgs and sum(len(str(m.content)) for m in system_msgs + other_msgs) > char_budget:
                if len(other_msgs) <= keep_intact_count:
                    other_msgs[0].content = "[Older context truncated to save tokens...]"
                    break
                other_msgs.pop(0)

            current_messages = system_msgs + other_msgs

        return current_messages

    async def _compact_messages(
        self,
        messages: list[BaseMessage],
        user_id: str | None = None,
        conversation_id: str | None = None,
        pinned_messages: list[str] | None = None
    ) -> list[BaseMessage]:
        """
        CC-inspired Context Compaction (OPT-5).
        Strategy: [System] + [Anchor T1] + [Compacted Middle] + [Recent N]
        """
        if not messages:
            return []

        async def episodic_callback(middle_msgs: list[BaseMessage], summary: str):
            """Internal wrapper to trigger episodic memory storage."""
            if user_id and conversation_id:
                try:
                    from app.services.memory.episodic_service import episodic_memory_service
                    # Format as serializable
                    serializable = []
                    for m in middle_msgs:
                        role = "user" if isinstance(m, HumanMessage) else "assistant"
                        serializable.append({"role": role, "content": str(m.content)})

                    await episodic_memory_service.store_episode(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        messages=serializable,
                        pre_computed_summary=summary
                    )
                except Exception as ex:
                    logger.warning(f"Episodic memory background task failed: {ex}")

        # Pass to the specialized compactor
        return await self.compactor.compact_messages(
            messages,
            on_compact_callback=episodic_callback,
            pinned_messages=pinned_messages
        )

    # ============================================================
    #  JSON Parsing Helpers
    # ============================================================

    @staticmethod
    def _parse_routing_decision(content: str) -> RoutingDecision:
        """Parse LLM output into RoutingDecision, with fallback."""
        cleaned = SwarmOrchestrator._clean_json(content)

        try:
            data = json.loads(cleaned)
            return RoutingDecision(**data)
        except Exception as e:
            logger.warning(f"Failed to parse routing JSON. Content: {cleaned[:200]!r}. Error: {e}")
            return RoutingDecision(
                next_agent="FINISH",
                uncertainty=1.0,
                reasoning="JSON extraction failed",
                task_refinement="",
            )

    @staticmethod
    def _parse_reflection_result(content: str) -> ReflectionResult:
        """Parse LLM output into ReflectionResult, with fallback."""
        cleaned = SwarmOrchestrator._clean_json(content)

        try:
            data = json.loads(cleaned)
            return ReflectionResult(**data)
        except Exception as e:
            logger.warning(f"Failed to parse reflection JSON. Content: {cleaned[:200]!r}. Error: {e}")
            # Default: approve to avoid infinite loops
            return ReflectionResult(
                quality_score=0.7,
                issues=[],
                suggestions=[],
                verdict="APPROVE",
            )

    @staticmethod
    def _clean_json(content: str) -> str:
        """Remove markdown code fences from LLM output."""
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return content.strip()

    # ============================================================
    #  Query Preprocessing (TASK-RAG-002)
    # ============================================================

    # Ambiguous pronouns that might refer to prior conversation context
    _AMBIGUOUS_PRONOUNS = frozenset([
        "它", "这个", "那个", "它们", "这些", "那些", "他", "她", "其",
        "this", "that", "it", "they", "these", "those", "them", "its",
    ])

    def _needs_rewrite(self, query: str) -> bool:
        """Quickly determine if a query likely has ambiguous references."""
        words = query.lower().split()
        if len(words) > 20:
            # Longer queries are usually self-contained
            return False
        return any(p in words or p in query for p in self._AMBIGUOUS_PRONOUNS)

    async def _preprocess_query(self, user_message: str) -> str:
        """
        Lightweight query rewrite at the Swarm input layer (TASK-RAG-002).

        Resolves ambiguous pronouns and completes vague queries BEFORE routing,
        so the supervisor can make better routing decisions for RAG queries.
        Only invokes the LLM when the query appears to contain ambiguous references.
        """
        if not self._needs_rewrite(user_message):
            return user_message

        try:
            llm = self.router.get_model(ModelTier.SIMPLE)
            prompt = (
                "You are a query clarification assistant.\n"
                "Rewrite the following user query to resolve any ambiguous pronouns "
                "(it, this, that, 它, 这个, etc.) and complete vague references. "
                "Return ONLY the rewritten query as a single line, no explanations.\n"
                "If the query is already clear, return it unchanged.\n\n"
                f"Original: {user_message}\nRewritten:"
            )
            resp = await llm.ainvoke([HumanMessage(content=prompt)])
            rewritten = resp.content.strip().splitlines()[0].strip()
            if rewritten and rewritten != user_message:
                logger.debug(f"[QueryPreprocess] Rewritten: '{user_message[:50]}' → '{rewritten[:50]}'")
                return rewritten
        except Exception as exc:
            logger.debug(f"[QueryPreprocess] Skipped (error): {exc}")
        return user_message

    # ============================================================
    #  Main Entry Point
    # ============================================================

    async def invoke(
        self, user_message: str, context: dict[str, Any] | None = None, conversation_id: str = "default_user"
    ) -> dict[str, Any]:
        """
        Main entry point with Atomic Initialization (M4 Fix).
        """
        await self.ensure_initialized()

        # TASK-RAG-002: Preprocess query — pronoun resolution + vague query completion
        user_message = await self._preprocess_query(user_message)

        # If context is provided (e.g., from Pipeline), augment the user message
        augmented_message = user_message
        if context:
            # Inject pipeline context as additional info
            stage_info = context.get("stage", "")
            if stage_info:
                augmented_message = f"[Pipeline Stage: {stage_info}]\n\n{user_message}"

        # Execute the graph
        config = {"configurable": {"thread_id": conversation_id}}
        assert self._graph is not None, "Graph must be compiled"
        final_state = await self._graph.ainvoke(initial_state, config=config)

        # --- GOV-EXP-001: Persist A/B Trace to DB (M4.1.4 Integration) ---
        try:
            from app.core.database import get_db_session
            from app.models.observability import SwarmTrace

            async def save_trace():
                async for db in get_db_session():
                    new_trace = SwarmTrace(
                        user_id=initial_state.get("user_id"),
                        query=user_message,
                        execution_variant=final_state.get("execution_variant"),
                        think_time_ms=sum(final_state.get("thinking_time_ms", [])),
                        tool_time_ms=sum(final_state.get("tool_time_ms", [])),
                        num_llm_calls=len(final_state.get("thinking_time_ms", [])),
                        latency_ms= (time.monotonic() - t_entry) * 1000 if 't_entry' in locals() else 0,
                        status="success"
                    )
                    db.add(new_trace)
                    await db.commit()
                    break

            # Fire and forget if non-critical, or await for consistency
            await save_trace()
        except Exception as e:
            logger.warning(f"Failed to persist swarm trace: {e}")

        return final_state

    async def invoke_stream(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
        history: list[BaseMessage] | None = None,
        conversation_id: str = "default_stream",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Streaming entry point with Atomic Initialization (M4 Fix).
        """
        await self.ensure_initialized()

        # TASK-RAG-002: Preprocess query — pronoun resolution + vague query completion
        user_message = await self._preprocess_query(user_message)

        messages = history.copy() if history else []
        augmented_message = user_message

        kb_ids = []
        if context:
            stage_info = context.get("stage", "")
            if stage_info:
                augmented_message = f"[Pipeline Stage: {stage_info}]\n\n{user_message}"
            kb_ids = context.get("knowledge_base_ids", [])

        messages.append(HumanMessage(content=augmented_message))

        import uuid
        initial_state: SwarmState = {
            "messages": messages,
            "next_step": "pre_processor",
            "agent_outputs": {},
            "uncertainty_level": 0.0,
            "current_task": user_message,
            "conversation_id": conversation_id,
            "swarm_trace_id": str(uuid.uuid4()),  # 🔗 [M5.1.4]
            "reflection_count": 0,
            "original_query": user_message,
            "context_data": context.get("context_data", "") if context else "",
            "kb_ids": kb_ids,
            "prompt_variant": context.get("prompt_variant", "default") if context else "default",
            "retrieval_variant": context.get("retrieval_variant", "default") if context else "default",
            # A/B: execution_variant assigned by pre_processor; allow override from context
            "execution_variant": context.get("execution_variant", "") if context else "",
            "thinking_time_ms": [],
            "tool_time_ms": [],
            "pinned_messages": context.get("pinned_messages", []) if context else [],
            "last_node_id": "",
            "parallel_agents": [],
            "retrieved_docs": context.get("retrieved_docs", []) if context else [],
            "status_update": None,
            "thought_log": None,
            "user_id": context.get("user_id") if context else None,
            "language": context.get("language", "zh-CN") if context else "zh-CN",
        }

        # Use LangGraph's streaming mode with config
        config = {"configurable": {"thread_id": conversation_id}}
        assert self._graph is not None, "Graph must be compiled before invocation"
        async for output in self._graph.astream(initial_state, config=config):
            # output is a dict like {'node_name': {state_updates}}
            yield output
