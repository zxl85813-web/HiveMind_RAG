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

import asyncio
import json
from typing import Annotated, Any, Literal, TypedDict, AsyncGenerator, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from app.agents.tools import NATIVE_TOOLS
from app.agents.agentic_search import SEARCH_TOOLS
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver 
from loguru import logger
from app.services.cache_service import CacheService # --- Guaranteed Import ---
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.memory import SharedMemoryManager
from app.agents.llm_router import LLMRouter, ModelTier
from app.services.cache_service import CacheService


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
    agent_outputs: dict[str, str]

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
    
    # Track Last Node Id for visual trace
    last_node_id: str

    # P2: RAG Retrieval Trace Logs
    retrieval_trace: List[str]
    retrieved_docs: List[dict]

    # --- Phase 5: Task Progress ---
    status_update: str | None
    thought_log: str | None
    
    # --- Phase 7: Permission Guard ---
    user_id: str | None

    # --- Multi-Tenant: tenant id propagated through every node ---
    tenant_id: str | None


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
    planned_steps: list[str] = Field(default_factory=list, description="Optional: decompose complex task into sub-tasks")


class ReflectionResult(BaseModel):
    """Reflection node's quality assessment."""
    quality_score: float = Field(description="0.0-1.0 quality assessment")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    verdict: str = Field(description="APPROVE | REVISE | ESCALATE")


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

        # --- LLM Router (Tiered Selection) ---
        self.router = LLMRouter()
        
        # --- Memory Manager ---
        self.memory = SharedMemoryManager()

        # --- PromptEngine (lazy import to avoid circular deps) ---
        self._prompt_engine = None
        
        # --- Services (Lazy load) ---
        self._retriever = None

        # --- MCP Manager ---
        from app.agents.mcp_manager import MCPManager
        self.mcp = MCPManager()

        # --- Skill Registry ---
        from app.skills.registry import SkillRegistry
        self.skills = SkillRegistry()

        logger.info(
            f"🐝 SwarmOrchestrator initialized with Tiered LLM Routing, MCP, and Skills"
        )

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
            tier = ModelTier.BALANCED
            
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

        # 2. Add Agent Nodes
        for name, agent_def in self._agents.items():
            workflow.add_node(name, self._create_agent_node(agent_def))

        # 3. Add Reflection Node
        workflow.add_node("reflection", self._reflection_node)

        # 4. Define Edges
        workflow.set_entry_point("pre_processor")
        workflow.add_conditional_edges(
            "pre_processor",
            lambda state: state["next_step"],
            {"supervisor": "supervisor", "FINISH": END}
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
                **{name: name for name in self._agents.keys()},
                "retrieval": "retrieval",
                "FINISH": END,
                "REFLECTION": "reflection",
                "PLATFORM_ACTION": "platform_action",
            }
        )

        # All agents → Reflection
        for name in self._agents.keys():
            workflow.add_edge(name, "reflection")

        # Reflection → Supervisor or END
        workflow.add_conditional_edges(
            "reflection",
            self._route_after_reflection,
            {"supervisor": "supervisor", "FINISH": END}
        )

        # 5. Compile with Checkpointer (Phase 5)
        checkpointer = MemorySaver()
        self._graph = workflow.compile(checkpointer=checkpointer)
        logger.info("🕸️ Swarm Graph compiled with Checkpointer Persistence")

    # ============================================================
    #  Supervisor Node — uses PromptEngine
    # ============================================================

    async def _pre_processor_node(self, state: SwarmState) -> dict:
        """Entry node for caching and JIT context checks."""
        query = state.get("original_query", "")
        
        # --- Semantic Cache Lookup (Architecture Layer 5 Middleware) ---
        cached = await CacheService.get_cached_response(query)
        if cached:
            logger.info(f"⚡ [Phase 4] Semantic Cache Hit: {query[:50]}...")
            return {
                "messages": [AIMessage(content=cached["content"])],
                "agent_outputs": {"cache": cached["content"]},
                "next_step": "FINISH"
            }
            
        return {"next_step": "supervisor"}

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
        # --- Context Compaction (2.1H) ---
        # Step 1: heuristic prune (count / budget / tool-result clearing).
        state["messages"] = self._prune_messages(state["messages"])
        # Step 2: LLM-driven summarisation when history is still large.
        state["messages"] = await self._compact_history(state["messages"])
        
        messages = state["messages"]
        user_query = str(state.get("original_query", "") or (messages[-1].content if messages else ""))
        
        # === Fast Path: Keyword-based Platform Action Detection ===
        # Intercept navigation intents BEFORE calling LLM for routing.
        # This is deterministic, cheap, and prevents hallucination in RAG agents.
        PLATFORM_INTENTS = [
            (
                ["创建知识库", "新建知识库", "create knowledge base", "create kb"],
                "open_modal:create_kb",
                '好的，现在为您打开**创建知识库**向导。\n[ACTION: {"type": "open_modal", "target": "create_kb", "label": "立刻创建", "variant": "primary"}]'
            ),
            (
                ["上传文档", "上传文件", "upload document", "upload file"],
                "navigate:/knowledge",
                '我来帮您跳转到**知识库管理**页面，在那里您可以上传文档。\n[ACTION: {"type": "navigate", "target": "/knowledge", "label": "去上传文档", "variant": "primary"}]'
            ),
            (
                ["去评测", "运行评测", "run evaluation", "跳转到评测"],
                "navigate:/evaluation",
                '好的，现在为您跳转到**评测中心**。\n[ACTION: {"type": "navigate", "target": "/evaluation", "label": "前往评测中心", "variant": "primary"}]'
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
                    "thought_log": f"⚡ 快速匹配: 检测到平台操作指令 '{keywords[0]}'"
                }

        # === Regular Path: Use LLM for routing ===
        # Build agent info for PromptEngine
        agents_info = [
            {"name": name, "description": a.description}
            for name, a in self._agents.items()
        ]
        # Add retrieval as a pseudo-agent for Adaptive RAG
        agents_info.append({
            "name": "retrieval",
            "description": "Knowledge Retrieval System. Route here if you need more context or factual information from the internal knowledge bases before answering."
        })

        # Build prompt via PromptEngine (Layer 1 + 2 + 3)
        system_prompt = self.prompt_engine.build_supervisor_prompt(
            agents=agents_info,
            memory_context=state.get("context_data", ""),
        )

        # --- Speculative Retrieval (Phase 6: Parallel Intent & Recall) ---
        # We start retrieval in parallel with the Router LLM.
        # This saves ~300-800ms of graph-hop latency and DB lookup time.
        retrieval_task = None
        # Always trigger if kb_ids is provided, or if query looks like research
        if state.get("kb_ids") or any(kw in user_query.lower() for kw in ["search", "find", "what", "how", "query", "搜索", "查询", "是啥", "什么"]):
            logger.info("⚡ [Phase 6] Starting speculative retrieval task...")
            retrieval_task = asyncio.create_task(self._do_retrieval_work(state))

        # Setup LLM and Prompt
        llm = self.router.get_model(ModelTier.FAST)
        final_prompt = [
            SystemMessage(content=system_prompt),
            *messages
        ]

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

        logger.info(
            f"👨‍✈️ Supervisor: {decision.next_agent} "
            f"(uncertainty={decision.uncertainty:.2f})"
        )

        next_step = decision.next_agent
        updates = {
            "next_step": next_step,
            "current_task": decision.reasoning,
        }

        # --- Phase 6: Speculative Pickup ---
        # If we already did retrieval and the supervisor says go to retrieval,
        # we can just merge the result HERE and skip the retrieval node's next-tick latency.
        if decision.next_agent == "retrieval" and pre_retrieval_result:
            logger.info("⚡ [Phase 6] Speculative Retrieval Hit! Merging results now.")
            updates.update(pre_retrieval_result)
            # Since we merged it, we can tell LangGraph to go back to supervisor 
            # or directly to an agent? No, keep the graph flow, but the retrieval node 
            # will now see the context is already there and be a no-op.
        # --- Phase 5: Task Scaffolding (Architecture Layer 2 Persistence) ---
        # If the LLM proposed a multi-step plan, persist it as a shared TODO list
        if decision.planned_steps:
             from app.models.agents import TodoItem, TodoStatus, TodoPriority
             for step in decision.planned_steps:
                 await self.memory.add_todo(TodoItem(
                     title=step,
                     status=TodoStatus.PENDING,
                     created_by="supervisor",
                     assigned_to=next_step,
                     source_conversation_id=state.get("conversation_id")
                 ))
             logger.info(f"📝 [Phase 5] Supervisor persisted plan with {len(decision.planned_steps)} steps to Memory.")

        logger.info(f"🗺️ Supervisor planned {len(decision.planned_steps)} steps")

        # Sensitivity flow monitor — record supervisor visit (passive).
        try:
            from app.services.governance import get_flow_monitor
            get_flow_monitor().record_node(
                state.get("conversation_id", "") or "", "supervisor"
            )
        except Exception:  # noqa: BLE001
            pass

        import uuid
        node_id = f"supervisor_{uuid.uuid4().hex[:6]}"

        return {
            "next_step": next_step,
            "uncertainty_level": decision.uncertainty,
            "current_task": decision.task_refinement,
            "last_node_id": node_id,
            "status_update": f"🗺️ Supervisor planned {len(decision.planned_steps)} steps" if decision.planned_steps else None,
            "thought_log": f"👨‍✈️ 决策路径: {decision.reasoning}"
        }

    # ============================================================
    #  Agent Node — uses PromptEngine
    # ============================================================

    def _create_agent_node(self, agent_def: AgentDefinition):
        """Factory for agent execution nodes with tool calling capability."""

        async def agent_node(state: SwarmState) -> dict:
            task = state.get("current_task", "")
            conv_id = state.get("conversation_id", "")
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
                # Add memory tools to all business agents
                available_tools.extend(NATIVE_TOOLS)
                # Add agentic search tools (Tier 0)
                available_tools.extend(SEARCH_TOOLS)
                # Add discovered MCP tools
                available_tools.extend(self.mcp.get_tools())
                # Add dynamically loaded Skills
                available_tools.extend(self.skills.get_all_tools())

            # --- Tool Auditing (Phase 3) ---
            from app.services.security.sanitizer import ToolAuditor, SecuritySanitizer
            system_prompt = self.prompt_engine.build_agent_prompt(
                agent_name=agent_def.name,
                task=task,
                rag_context=state.get("context_data", ""),
                memory_context="", # TODO: inject episodic memory
                tools_available=[t.name for t in available_tools if hasattr(t, "name")],
            )

            # 3. Get the appropriate LLM and bind tools
            llm = self._get_llm_for_agent(agent_def)
            if available_tools:
                llm = llm.bind_tools(available_tools)

            # --- Context Compaction (2.1H) ---
            state["messages"] = self._prune_messages(state["messages"])

            # 4. Invoke LLM (with tool-calling loop)
            # We perform a simple ReAct loop inside the node for native tools
            current_messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
            current_messages.extend(state["messages"])
            
            # Max 3 tool iterations to avoid infinite loops within a single node
            for _ in range(3):
                response = await llm.ainvoke(current_messages)
                current_messages.append(response)
                
                if not response.tool_calls:
                    break
                
                tool_names = [tc['name'] for tc in response.tool_calls]
                logger.info(f"🛠️ Agent [{agent_def.name}] calling tools: {tool_names}")
                
                # --- Immediate Thought Update for Tools ---
                # We can't easily yield from here, but we can put it in a log list if we use Annotated
                # For now, we rely on the node completion or the next iteration
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Find and execute tool
                    tool_obj = next((t for t in available_tools if getattr(t, "name", "") == tool_name), None)
                    if tool_obj:
                        # Append agent name if tool supports it (for memory logging)
                        if "agent_name" in tool_args:
                            tool_args["agent_name"] = agent_def.name
                    
                        # Audit tool call (Phase 3)
                        if not ToolAuditor.audit_tool_call(tool_name, tool_args):
                            result = "Error: Tool call blocked by security policy."
                        else:
                            result = await tool_obj.ainvoke(tool_args)

                        # Sensitivity monitor — passive tool-call counting.
                        try:
                            from app.services.governance import get_flow_monitor
                            get_flow_monitor().record_tool(
                                state.get("conversation_id", "") or "",
                                tool_name,
                                tool_args if isinstance(tool_args, dict) else None,
                            )
                        except Exception:  # noqa: BLE001
                            pass

                        current_messages.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            content=str(result)
                        ))
                    else:
                        current_messages.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            content=f"Error: Tool '{tool_name}' not found."
                        ))

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

            return {
                "messages": new_messages,
                "agent_outputs": {agent_def.name: str(final_content)},
                "last_node_id": node_id,
                "status_update": f"✅ {agent_def.name} finished work."
            }

        return agent_node

    # ============================================================
    #  Platform Action Node — handles UI navigation/modal requests
    # ============================================================

    async def _platform_action_node(self, state: SwarmState) -> dict:
        """
        Platform Action node — directly emits a pre-built response with [ACTION: ...] tag.
        
        This node bypasses all specialist agents and LLM inference.
        The reply template was set by the Supervisor's fast path keyword detection.
        """
        # The Supervisor fast path stores the reply template in context_data
        reply = state.get("context_data", "好的，正在为您操作...")
        
        logger.info(f"[PlatformAction] Responding with direct action reply")
        
        return {
            "messages": [AIMessage(content=reply)],
            "agent_outputs": {"platform_action": reply},
        }

    # ============================================================
    #  Reflection Node — uses PromptEngine + LLM
    # ============================================================

    async def _reflection_node(self, state: SwarmState) -> dict:
        """
        Reflection node — evaluates agent output quality using LLM.

        Uses PromptEngine's reflection template.
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

        # Determine which agent produced the last output
        agent_outputs = state.get("agent_outputs", {})
        last_agent_name = list(agent_outputs.keys())[-1] if agent_outputs else "unknown"

        # Build reflection prompt via PromptEngine
        reflection_prompt = self.prompt_engine.build_reflection_prompt(
            user_query=state.get("original_query", ""),
            agent_name=last_agent_name,
            agent_response=last_message.content[:1500],  # Truncate to save tokens
            task_description=state.get("current_task", ""),
        )

        # Invoke LLM for quality check (using BALANCED or FAST)
        # --- Advanced Multi-Grader Evaluation (Phase 3) ---
        from app.services.evaluation.multi_grader import MultiGraderEval
        evaluator = MultiGraderEval()
        
        eval_result = await evaluator.evaluate(
            query=state.get("original_query", ""),
            response=last_message.content,
            context=state.get("context_data", ""),
            known_citation_ids=[
                c.get("citation_id") if isinstance(c, dict) else getattr(c, "citation_id", None)
                for c in (state.get("retrieval_trace", {}) or {}).get("citations", [])
                if c
            ] or None,
        )

        # Hybrid Reflection: a hard-rule veto must NOT be cached and must
        # short-circuit the loop so we don't waste turns flattering a bad
        # response.
        if eval_result.hard_rule_vetoed:
            logger.warning(
                f"🚦 [HardRules] VETO — forcing revision ({eval_result.hard_rule_summary})"
            )

        # --- Automatic Semantic Caching (Phase 4) ---
        if (
            eval_result.verdict in ["PASS", "EXCELLENT"]
            and eval_result.composite_score >= 0.8
            and not eval_result.hard_rule_vetoed
        ):
            from app.services.cache_service import CacheService
            import asyncio
            # background task to cache the result
            asyncio.create_task(CacheService.set_cached_response(
                query=state.get("original_query", ""),
                response=last_message.content,
                metadata={"agent": last_agent_name, "score": eval_result.composite_score}
            ))
            logger.info(f"💾 [Phase 4] Queued high-quality response for semantic cache.")

        # Decide next step based on composite score
        if eval_result.verdict in ["PASS", "EXCELLENT"]:
            next_step = "FINISH"
        else:
            next_step = "supervisor" # REVISE

        logger.info(
            f"🧪 [MultiGrader] Verdict: {eval_result.verdict} "
            f"(score={eval_result.composite_score:.2f})"
        )

        # --- Production Governance (2.1J) ---
        # 1. Sensitivity flow monitoring — passive, never blocks.
        # 2. Shadow eval sampler — only fires on FINISH (real production
        #    response), and only for the configured sample rate.
        try:
            from app.services.governance import (
                get_flow_monitor,
                get_shadow_eval_sampler,
                get_rainbow_router,
            )

            conv_id = state.get("conversation_id", "") or ""
            monitor = get_flow_monitor()
            monitor.record_node(conv_id, "reflection")

            if next_step == "FINISH" and conv_id:
                ring = get_rainbow_router().pick_ring(conv_id)
                get_shadow_eval_sampler().maybe_evaluate(
                    conversation_id=conv_id,
                    query=state.get("original_query", ""),
                    response=last_message.content,
                    context=state.get("context_data", ""),
                    known_citation_ids=[
                        c.get("citation_id") if isinstance(c, dict)
                        else getattr(c, "citation_id", None)
                        for c in (state.get("retrieval_trace", {}) or {}).get("citations", [])
                        if c
                    ] or None,
                    ring=ring.name if ring else None,
                )
        except Exception as gov_err:  # noqa: BLE001
            # Governance must never fail a real request.
            logger.debug(f"governance hooks skipped: {gov_err}")

        import uuid
        node_id = f"reflection_{uuid.uuid4().hex[:6]}"

        return {
            "reflection_count": reflection_count,
            "next_step": next_step,
            "last_node_id": node_id,
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
        """Core retrieval logic shared by node and pre-warmer.

        Goes through the unified ``RAGGateway`` so Agents share the exact
        protocol consumed by the REST API and Skill tools. The gateway
        returns a structured ``KnowledgeResponse``; we keep ``context_data``
        as a pre-rendered prompt block (with citation tags) for backward
        compatibility with downstream agent prompts, and additionally
        stash the structured fragments in ``retrieved_docs`` for any
        agent / UI that wants to render them.
        """
        query = str(state.get("original_query", ""))

        context_str = ""
        kb_ids = state.get("kb_ids", [])
        retrieval_trace: List[str] = []
        retrieved_docs: List[dict] = []
        knowledge_res = None

        try:
            # 1. Auto-route KBs if none specified.
            if not kb_ids:
                from app.services.retrieval.routing import KnowledgeBaseSelector
                selector = KnowledgeBaseSelector()
                selected_kbs = await selector.select_kbs(query)
                kb_ids = [kb.id for kb in selected_kbs]

            if kb_ids:
                # 2. Resolve DB KB ids → vector collection names + ACL filter.
                from app.core.database import async_session_factory
                from app.models.knowledge import KnowledgeBase
                from app.models.chat import User
                from app.services.knowledge.kb_service import KnowledgeService

                collection_to_kb: dict[str, str] = {}
                async with async_session_factory() as db_session:
                    user_id = state.get("user_id")

                    accessible_kbs = None
                    if user_id:
                        user = await db_session.get(User, user_id)
                        if user:
                            svc = KnowledgeService(db_session)
                            accessible_kbs = await svc.get_user_accessible_kbs(user)

                    for kid in kb_ids:
                        if accessible_kbs is not None and kid not in accessible_kbs:
                            logger.warning(
                                f"Skipping KB {kid} (no permission for user {user_id})"
                            )
                            continue
                        kb = await db_session.get(KnowledgeBase, kid)
                        if kb and kb.vector_collection:
                            collection_to_kb[kb.vector_collection] = kid

                # 3. Drive the unified RAGGateway.
                if collection_to_kb:
                    from app.services.rag_gateway import get_rag_gateway

                    gateway = get_rag_gateway()
                    knowledge_res = await gateway.retrieve(
                        query=query,
                        kb_ids=list(collection_to_kb.keys()),
                        top_k=3,
                        recall_top_k=20,
                        strategy="hybrid",
                        user_id=str(state.get("user_id")) if state.get("user_id") else None,
                    )

                    # Map gateway's "kb_id" (=collection_name) back to the
                    # public DB id so downstream consumers don't see internals.
                    for frag in knowledge_res.fragments:
                        public_kb = collection_to_kb.get(frag.kb_id)
                        if public_kb:
                            frag.kb_id = public_kb
                            if frag.citation:
                                frag.citation.kb_id = public_kb

                    retrieval_trace = knowledge_res.extensions.get("trace", []) or []
                    retrieval_trace.extend(knowledge_res.warnings)
                    retrieved_docs = [f.model_dump() for f in knowledge_res.fragments]

                    if knowledge_res.fragments:
                        context_str = (
                            "--- DEEP CONTEXT (RAG) ---\n"
                            + knowledge_res.to_prompt_context()
                        )
                        if knowledge_res.citations:
                            context_str += "\n\n--- CITATIONS ---\n" + "\n".join(
                                f"[^{c.citation_id}] {c.document_title or c.source_id}"
                                + (f" (p.{c.page})" if c.page else "")
                                for c in knowledge_res.citations
                            )
        except Exception as e:  # noqa: BLE001
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

    async def _compact_history(
        self,
        messages: List[BaseMessage],
        *,
        trigger_message_count: int = 18,
        trigger_char_count: int = 14000,
        keep_recent: int = 6,
    ) -> List[BaseMessage]:
        """LLM-driven summarisation of stale history.

        When the conversation gets long enough that the cheap heuristic
        prune can no longer keep us under budget, we ask the FAST tier
        LLM to fold the older non-system messages into a single
        ``SystemMessage`` summary. The most recent ``keep_recent``
        messages are preserved verbatim so the agent retains short-term
        focus and tool call/response coherence.

        Failure of the summarisation call is non-fatal: we fall back to
        returning the input unchanged.
        """
        if not messages:
            return messages

        non_system = [m for m in messages if not isinstance(m, SystemMessage)]
        total_chars = sum(len(str(m.content)) for m in non_system)
        if (
            len(non_system) <= trigger_message_count
            and total_chars <= trigger_char_count
        ):
            return messages

        # Slice off the older window to compact.
        if len(non_system) <= keep_recent:
            return messages
        head = non_system[:-keep_recent]
        tail = non_system[-keep_recent:]
        if not head:
            return messages

        # Render head into a compact transcript for the summariser.
        transcript_lines = []
        for m in head:
            role = type(m).__name__.replace("Message", "").lower()
            content = str(m.content)
            if len(content) > 1200:
                content = content[:1200] + "…"
            transcript_lines.append(f"[{role}] {content}")
        transcript = "\n".join(transcript_lines)

        try:
            llm = self.router.get_model(ModelTier.FAST)
            prompt = (
                "You are a context compactor. Summarise the following "
                "agent/user transcript in <= 200 words. Preserve: user "
                "goals, decisions made, tool outputs that affect future "
                "steps, and any pending TODOs. Drop chit-chat.\n\n"
                f"TRANSCRIPT:\n{transcript}\n\nSUMMARY:"
            )
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            summary = str(getattr(response, "content", "") or "").strip()
            if not summary:
                return messages
            logger.info(
                f"🗜️ [Compaction] Folded {len(head)} msgs "
                f"({total_chars} chars) → {len(summary)}-char summary."
            )
            system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
            digest = SystemMessage(
                content=(
                    "[Conversation summary so far — older history was "
                    f"compacted to save tokens]\n{summary}"
                )
            )
            return system_msgs + [digest] + tail
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Context compaction failed, keeping raw history: {e}")
            return messages

    def _prune_messages(self, messages: List[BaseMessage], max_messages: int = 25, char_budget: int = 24000) -> List[BaseMessage]:
        """
        Prunes message history to stay within token/char limits.
        Uses 'Tool Result Clearing' for older tool calls and keeps a strict character budget.
        """
        if not messages:
            return []

        # 1. Message Count Pruning
        if len(messages) > max_messages:
            logger.info(f"🧹 [Phase 6] Pruning by count: {len(messages)} -> {max_messages}")
            # Keep system, and last max_messages
            system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
            other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
            messages = system_msgs + other_msgs[-(max_messages - len(system_msgs)):]

        # 2. Tool Result Clearing (Content-based)
        # We always keep the last 6 messages completely intact
        keep_intact_count = 6
        head_msgs = messages[:-keep_intact_count] if len(messages) > keep_intact_count else []
        tail_msgs = messages[-keep_intact_count:] if len(messages) > keep_intact_count else messages

        refined_head = []
        for msg in head_msgs:
            if isinstance(msg, ToolMessage) and len(str(msg.content)) > 150:
                # Clear content but keep tool result status/summary
                summary = f"[Output of {msg.tool_call_id[:8]}... summarized: {len(str(msg.content))} chars truncated]"
                refined_head.append(ToolMessage(tool_call_id=msg.tool_call_id, content=summary))
            else:
                refined_head.append(msg)
        
        current_messages = refined_head + tail_msgs

        # 3. Total Character Budget Check
        total_chars = sum(len(str(m.content)) for m in current_messages)
        if total_chars > char_budget:
            logger.info(f"⚖️ [Phase 6] Budget exceeded ({total_chars} > {char_budget}). Removing intermediate history.")
            # Drop older messages (after system) until within budget
            system_msgs = [m for m in current_messages if isinstance(m, SystemMessage)]
            other_msgs = [m for m in current_messages if not isinstance(m, SystemMessage)]
            
            while other_msgs and sum(len(str(m.content)) for m in system_msgs + other_msgs) > char_budget:
                if len(other_msgs) <= keep_intact_count:
                    # Don't prune the very end, just truncate the oldest among them
                    other_msgs[0].content = "[Older context truncated to save tokens...]"
                    break
                other_msgs.pop(0)
            
            current_messages = system_msgs + other_msgs

        return current_messages

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
            logger.warning(f"Failed to parse routing JSON. Content: {repr(cleaned[:200])}. Error: {e}")
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
            logger.warning(f"Failed to parse reflection JSON. Content: {repr(cleaned[:200])}. Error: {e}")
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

    async def _enforce_budget(
        self,
        tenant_id: str,
        *,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        """Trip the budget circuit-breaker if today's tenant spend is over quota.

        Raises ``BudgetExceededError`` (-> HTTP 429). Best-effort: failure to
        check the gate (e.g. DB unavailable) does NOT block the call.
        """
        try:
            from app.core.database import get_db_session
            from app.services.governance.token_accountant import get_budget_gate
            gate = get_budget_gate()
            async for session in get_db_session():
                await gate.check(
                    session, tenant_id,
                    user_id=user_id, conversation_id=conversation_id,
                )
                break
        except ImportError:
            return
        except Exception as exc:
            from app.core.exceptions import BudgetExceededError
            from app.services.governance.rate_limiter import RateLimitExceeded
            if isinstance(exc, (BudgetExceededError, RateLimitExceeded)):
                raise
            logger.warning("Budget gate check failed (allowing): {}", exc)

    # ============================================================
    #  Main Entry Point
    # ============================================================

    async def invoke(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
        conversation_id: str = "default_user"
    ) -> dict[str, Any]:
        """
        Main entry point — process a user request through the swarm.
        """
        if not self._graph:
            await self.build_graph()

        # If context is provided (e.g., from Pipeline), augment the user message
        augmented_message = user_message
        if context:
            # Inject pipeline context as additional info
            pipeline_info = context.get("pipeline_context", {})
            stage_info = context.get("stage", "")
            if stage_info:
                augmented_message = (
                    f"[Pipeline Stage: {stage_info}]\n\n"
                    f"{user_message}"
                )

        initial_state: SwarmState = {
            "messages": [HumanMessage(content=augmented_message)],
            "next_step": "pre_processor",
            "agent_outputs": {},
            "uncertainty_level": 0.0,
            "current_task": user_message,
            "conversation_id": conversation_id,
            "reflection_count": 0,
            "original_query": user_message,
            "context_data": "",
            "kb_ids": context.get("knowledge_base_ids", []) if context else [],
            "last_node_id": "",
            "retrieval_trace": [],
            "retrieved_docs": [],
            "status_update": None,
            "thought_log": None,
            "user_id": context.get("user_id") if context else None,
            "tenant_id": (context or {}).get("tenant_id"),
        }

        # Bind tenant for the lifetime of this graph run so every
        # singleton (FlowMonitor / SemanticIdMapper / SkillMiner / ...)
        # reads tenant-scoped state. Falls back to the active context
        # tenant (set by the FastAPI dependency) when caller didn't pass one.
        from app.core.tenant_context import (
            get_current_tenant,
            tenant_scope,
        )
        tenant_id = initial_state["tenant_id"] or get_current_tenant()
        initial_state["tenant_id"] = tenant_id
        user_id = initial_state.get("user_id")

        # Execute the graph with config for checkpointer
        config = {"configurable": {"thread_id": conversation_id}}
        assert self._graph is not None, "Graph must be compiled"
        with tenant_scope(tenant_id, user_id=user_id, conversation_id=conversation_id):
            await self._enforce_budget(tenant_id, user_id=user_id, conversation_id=conversation_id)
            final_state = await self._graph.ainvoke(initial_state, config=config)
        return final_state

    async def invoke_stream(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
        history: list[BaseMessage] | None = None,
        conversation_id: str = "default_stream"
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Streaming version of invoke — yields intermediate updates/events.
        """
        if not self._graph:
            await self.build_graph()

        messages = history.copy() if history else []
        augmented_message = user_message
        
        kb_ids = []
        if context:
            pipeline_info = context.get("pipeline_context", {})
            stage_info = context.get("stage", "")
            if stage_info:
                augmented_message = (
                    f"[Pipeline Stage: {stage_info}]\n\n"
                    f"{user_message}"
                )
            kb_ids = context.get("knowledge_base_ids", [])

        messages.append(HumanMessage(content=augmented_message))

        initial_state: SwarmState = {
            "messages": messages,
            "next_step": "pre_processor",
            "agent_outputs": {},
            "uncertainty_level": 0.0,
            "current_task": user_message,
            "conversation_id": conversation_id,
            "reflection_count": 0,
            "original_query": user_message,
            "context_data": "",
            "kb_ids": kb_ids, # Pass to state
            "last_node_id": "", # Init empty
            "retrieval_trace": [],
            "retrieved_docs": [],
            "status_update": None,
            "thought_log": None,
            "user_id": context.get("user_id") if context else None,
            "tenant_id": (context or {}).get("tenant_id"),
        }

        from app.core.tenant_context import (
            get_current_tenant,
            tenant_scope,
        )
        tenant_id = initial_state["tenant_id"] or get_current_tenant()
        initial_state["tenant_id"] = tenant_id
        user_id = initial_state.get("user_id")

        # Use LangGraph's streaming mode with config
        config = {"configurable": {"thread_id": conversation_id}}
        assert self._graph is not None, "Graph must be compiled before invocation"
        with tenant_scope(tenant_id, user_id=user_id, conversation_id=conversation_id):
            await self._enforce_budget(tenant_id, user_id=user_id, conversation_id=conversation_id)
            async for output in self._graph.astream(initial_state, config=config):
                # output is a dict like {'node_name': {state_updates}}
                yield output
