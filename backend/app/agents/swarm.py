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

import json
from typing import Annotated, Any, Literal, TypedDict, AsyncGenerator, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from app.agents.tools import NATIVE_TOOLS
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.memory import SharedMemoryManager
from app.agents.llm_router import LLMRouter, ModelTier


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


# ============================================================
#  Structured Outputs
# ============================================================

class RoutingDecision(BaseModel):
    """Supervisor's decision on how to route the request."""
    next_agent: str = Field(description="The name of the next agent to invoke, or 'FINISH'")
    uncertainty: float = Field(description="Confidence score (0.0 = confident, 1.0 = uncertain)")
    reasoning: str = Field(description="Reason for this routing decision")
    task_refinement: str = Field(description="Refined description of the task for the agent")


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
        workflow.set_entry_point("supervisor")
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

        self._graph = workflow.compile()
        logger.info("🕸️ Swarm Graph compiled successfully")

    # ============================================================
    #  Supervisor Node — uses PromptEngine
    # ============================================================

    async def _supervisor_node(self, state: SwarmState) -> dict:
        """
        [溯源]: 项目架构核心 / REQ-Orchestrator
        [设计决策]: 
        Supervisor node — 意图识别与路由节点。
        在此节点中，我们没有完全依赖 LLM 来做路由，而是前置了一个【关键字硬编码快速判断（Fast Path）】。
        这是为了极大降低平台操作（如页面跳转、弹窗提示）的响应延迟，避免 RAG 幻觉。
        
        [🛡️ AI-LOCKED (AI 修改禁区)]:
        绝对不要把这里的 Fast Path 逻辑给删掉，也不要强行用 LLM 覆盖这个兜底逻辑。如果需要新增快速匹配命令，请在 `PLATFORM_INTENTS` 数组中追加。
        """
        messages = state["messages"]
        user_query = state.get("original_query", "") or (messages[-1].content if messages else "")
        
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

        # Invoke LLM using FAST tier for supervisor routing
        llm = self.router.get_model(ModelTier.FAST)
        
        final_prompt = [
            SystemMessage(content=system_prompt),
            *messages
        ]

        response = await llm.ainvoke(final_prompt)
        content = response.content

        # Parse JSON (with markdown cleanup)
        decision = self._parse_routing_decision(content)

        logger.info(
            f"👨‍✈️ Supervisor: {decision.next_agent} "
            f"(uncertainty={decision.uncertainty:.2f}, reason={decision.reasoning[:50]})"
        )

        next_step = decision.next_agent
        if decision.uncertainty > 0.7:
            # High uncertainty — could trigger debate in future
            pass

        import uuid
        node_id = f"supervisor_{uuid.uuid4().hex[:6]}"
        await self.memory.add_trace(
            node_id=node_id,
            label="Intent Analysis & Routing",
            agent="Supervisor",
            status="completed",
            targets=[f"{next_step}_node"] if next_step != "FINISH" else []
        )

        return {
            "next_step": next_step,
            "uncertainty_level": decision.uncertainty,
            "current_task": decision.task_refinement,
            "last_node_id": node_id,
        }

    # ============================================================
    #  Agent Node — uses PromptEngine
    # ============================================================

    def _create_agent_node(self, agent_def: AgentDefinition):
        """Factory for agent execution nodes with tool calling capability."""

        async def agent_node(state: SwarmState) -> dict:
            task = state.get("current_task", "")
            logger.info(f"🤖 Agent [{agent_def.name}] working on: {task[:80]}")

            # 1. Prepare Tools
            # Combine native tools with agent-specific tools, and MCP tools
            available_tools = list(agent_def.tools)
            if agent_def.name != "supervisor":
                # Add memory tools to all business agents
                available_tools.extend(NATIVE_TOOLS)
                # Add discovered MCP tools
                available_tools.extend(self.mcp.get_tools())
                # Add dynamically loaded Skills
                available_tools.extend(self.skills.get_all_tools())

            # 2. Build prompt via PromptEngine
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
                
                logger.info(f"🛠️ Agent [{agent_def.name}] calling tools: {[tc['name'] for tc in response.tool_calls]}")
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Find and execute tool
                    tool_obj = next((t for t in available_tools if getattr(t, "name", "") == tool_name), None)
                    if tool_obj:
                        # Append agent name if tool supports it (for memory logging)
                        if "agent_name" in tool_args:
                            tool_args["agent_name"] = agent_def.name
                            
                        result = await tool_obj.ainvoke(tool_args)
                        current_messages.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            content=str(result)
                        ))
                    else:
                        current_messages.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            content=f"Error: Tool '{tool_name}' not found."
                        ))

            # 5. Extract results
            # The final AI message is usually the last one, but we might have tool results last
            # We want the content of the most recent AIMessage for agent_outputs
            final_ai_msg = next((m for m in reversed(current_messages) if isinstance(m, AIMessage)), None)
            final_content = final_ai_msg.content if final_ai_msg else "Task completed with tools."

            new_msgs_count = len(current_messages) - (1 + len(state["messages"]))
            new_messages = current_messages[-new_msgs_count:] if new_msgs_count > 0 else []

            import uuid
            node_id = f"{agent_def.name}_{uuid.uuid4().hex[:6]}"
            await self.memory.add_trace(
                node_id=node_id,
                label=f"Task Execution",
                agent=agent_def.name,
                status="completed",
                targets=["reflection_node"]
            )

            # Record node linkage for frontend DAG trace
            if state.get("last_node_id"):
                # We could link the supervisor to this node, but we'll let frontend link it 
                # or just use sequential linking if we want.
                pass

            return {
                "messages": new_messages,
                "agent_outputs": {agent_def.name: str(final_content)},
                "last_node_id": node_id,
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
        llm = self.router.get_model(ModelTier.BALANCED)
        response = await llm.ainvoke([
            SystemMessage(content=reflection_prompt),
        ])

        # Parse reflection result
        reflection = self._parse_reflection_result(response.content)

        logger.info(
            f"🪞 Reflection: score={reflection.quality_score:.2f}, "
            f"verdict={reflection.verdict}"
        )

        # Decide next step based on reflection
        if reflection.verdict == "APPROVE" or reflection.quality_score >= 0.7:
            next_step = "FINISH"
        elif reflection.verdict == "ESCALATE":
            next_step = "supervisor"  # Route to a different agent
        else:
            next_step = "supervisor"  # REVISE — let supervisor re-route

        import uuid
        node_id = f"reflection_{uuid.uuid4().hex[:6]}"
        await self.memory.add_trace(
            node_id=node_id,
            label="Quality Reflection",
            agent="Reflection",
            status="completed" if next_step == "FINISH" else "warning",
            targets=[f"{next_step}_node"] if next_step != "FINISH" else []
        )

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
        Retrieval node — fetches context from Radar, Graph, and Vector tiers.
        """
        raw_query = state.get("original_query", "")
        query: str = str(raw_query)
        # Use a safe slice or just a string
        display_query = query if len(query) < 40 else query[:40]
        logger.info(f"🔍 Retrieval Tier: Searching for '{display_query}...'")

        context_str = ""
        kb_ids = []
        
        # Pull context passed from view
        # We need a way to get kb_ids from context, but context isn't in SwarmState.
        # Actually, let's just do Vector Tier using RetrievalPipeline
        try:
            from app.services.retrieval.pipeline import get_retrieval_service
            if not self._retriever:
                self._retriever = get_retrieval_service()
            
            # TODO get kb_ids from state if stored
            # We can store kb_ids in SwarmState if needed
            kb_ids = state.get("kb_ids", [])
            
            if not kb_ids:
                # Use query routing
                from app.services.retrieval.routing import KnowledgeBaseSelector
                selector = KnowledgeBaseSelector()
                selected_kbs = await selector.select_kbs(query)
                kb_ids = [kb.id for kb in selected_kbs]
                
            if kb_ids:
                # Convert kb_ids to vector_collection names
                from sqlmodel import Session
                from app.core.database import engine
                from app.models.knowledge import KnowledgeBase
                
                collection_names = []
                with Session(engine) as session:
                    for kid in kb_ids:
                        kb = session.get(KnowledgeBase, kid)
                        if kb and kb.vector_collection:
                            collection_names.append(kb.vector_collection)
                
                if collection_names:
                    docs, retrieval_logs = await self._retriever.run(
                        query=query,
                        collection_names=collection_names,
                        top_k=5,
                        top_n=3
                    )
                    
                    # Store trace logs in state
                    retrieval_trace = retrieval_logs
                    retrieved_docs = [d.dict() for d in docs]
                    
                    if docs:
                        context_str += "--- DEEP CONTEXT (RAG) ---\n"
                        for i, d in enumerate(docs):
                            # Append citation footnote
                            page = d.metadata.get("page", "?")
                            file_name = d.metadata.get("file_name", "Unknown File")
                            context_str += f"[{i+1}] Source: {file_name} (Page {page})\n{d.page_content}\n"
        except Exception as e:
            logger.warning(f"Retrieval tier error: {e}")

        import uuid
        node_id = f"retrieval_{uuid.uuid4().hex[:6]}"
        await self.memory.add_trace(
            node_id=node_id,
            label="Memory & Web Retrieval",
            agent="Knowledge Router",
            status="completed",
            targets=["supervisor_node"]
        )

        return {
            "context_data": context_str,
            "last_node_id": node_id,
            "retrieval_trace": locals().get("retrieval_trace", []),
            "retrieved_docs": locals().get("retrieved_docs", [])
        }

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

    # ============================================================
    #  Main Entry Point
    # ============================================================

    async def invoke(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Main entry point — process a user request through the swarm.

        Args:
            user_message: The user's input message
            context: Optional context (e.g., from Pipeline upstream artifacts)

        Returns:
            Final SwarmState dict containing messages, agent_outputs, etc.
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
            "next_step": "supervisor",
            "agent_outputs": {},
            "uncertainty_level": 0.0,
            "current_task": user_message,
            "reflection_count": 0,
            "original_query": user_message,
            "context_data": "",
            "kb_ids": [],
            "last_node_id": "",
            "retrieval_trace": [],
            "retrieved_docs": [],
        }

        # Execute the graph
        assert self._graph is not None, "Graph must be compiled"
        final_state = await self._graph.ainvoke(initial_state)
        return final_state

    async def invoke_stream(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
        history: list[BaseMessage] | None = None,
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
            "next_step": "supervisor",
            "agent_outputs": {},
            "uncertainty_level": 0.0,
            "current_task": user_message,
            "reflection_count": 0,
            "original_query": user_message,
            "context_data": "",
            "kb_ids": kb_ids, # Pass to state
            "last_node_id": "", # Init empty
            "retrieval_trace": [],
        }

        # Use LangGraph's streaming mode
        assert self._graph is not None, "Graph must be compiled before invocation"
        async for output in self._graph.astream(initial_state):
            # output is a dict like {'node_name': {state_updates}}
            yield output
