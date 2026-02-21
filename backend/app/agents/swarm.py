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
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.memory import SharedMemoryManager


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

        # --- LLM instances (per model_hint) ---
        self._llm_cache: dict[str, ChatOpenAI] = {}
        self._default_llm = self._create_llm(settings.LLM_MODEL)
        
        # --- Memory Manager ---
        self.memory = SharedMemoryManager()

        # --- PromptEngine (lazy import to avoid circular deps) ---
        self._prompt_engine = None

        logger.info(
            f"🐝 SwarmOrchestrator initialized "
            f"(model={settings.LLM_MODEL}, provider={settings.LLM_PROVIDER})"
        )

    # ============================================================
    #  Agent Management
    # ============================================================

    def get_agents(self) -> dict[str, AgentDefinition]:
        """Return all registered agents."""
        return self._agents

    # ============================================================
    #  LLM Management
    # ============================================================

    def _create_llm(self, model: str | None = None, temperature: float = 0) -> ChatOpenAI:
        """Create a ChatOpenAI instance with current provider config."""
        llm_kwargs: dict[str, Any] = {
            "model": model or settings.LLM_MODEL,
            "temperature": temperature,
        }

        if settings.LLM_PROVIDER == "siliconflow":
            llm_kwargs["base_url"] = settings.LLM_BASE_URL
            llm_kwargs["api_key"] = settings.LLM_API_KEY
        elif settings.LLM_PROVIDER == "openai":
            if settings.OPENAI_API_KEY:
                llm_kwargs["api_key"] = settings.OPENAI_API_KEY

        return ChatOpenAI(**llm_kwargs)

    def _get_llm_for_agent(self, agent_def: AgentDefinition) -> ChatOpenAI:
        """
        Get the appropriate LLM for an agent based on model_hint.

        model_hint mapping (configurable):
            "fast"      → uses default model (quick responses)
            "balanced"  → uses default model
            "reasoning" → uses default model (in production: stronger model)

        When LLM Router is implemented, this will use it for smart routing.
        """
        # For now, all hints map to default model
        # TODO: When LLM Router is ready, use different models per hint
        hint = agent_def.model_hint or "balanced"

        if hint not in self._llm_cache:
            # In future: map hint → specific model
            self._llm_cache[hint] = self._default_llm

        return self._llm_cache[hint]

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
            del self._agents[name]
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

        Graph structure:
        START → supervisor → [agent_nodes] → reflection → supervisor/END
        """
        workflow = StateGraph(SwarmState)

        # 1. Add Supervisor Node
        workflow.add_node("supervisor", self._supervisor_node)

        # 2. Add Agent Nodes
        for name, agent_def in self._agents.items():
            workflow.add_node(name, self._create_agent_node(agent_def))

        # 3. Add Reflection Node
        workflow.add_node("reflection", self._reflection_node)

        # 4. Define Edges
        workflow.set_entry_point("supervisor")

        # Supervisor → Agent or END
        workflow.add_conditional_edges(
            "supervisor",
            lambda state: state["next_step"],
            {
                **{name: name for name in self._agents.keys()},
                "FINISH": END,
                "REFLECTION": "reflection",
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
        Supervisor node — analyzes intent and routes to agents.

        Uses PromptEngine to build the prompt from YAML + Jinja2 templates.
        """
        messages = state["messages"]

        # Build agent info for PromptEngine
        agents_info = [
            {"name": name, "description": a.description}
            for name, a in self._agents.items()
        ]

        # Build prompt via PromptEngine (Layer 1 + 2 + 3)
        system_prompt = self.prompt_engine.build_supervisor_prompt(
            agents=agents_info,
            memory_context="",  # TODO: inject from SharedMemoryManager
        )

        # Invoke LLM
        final_prompt = [
            SystemMessage(content=system_prompt),
            *messages
        ]

        response = await self._default_llm.ainvoke(final_prompt)
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

        return {
            "next_step": next_step,
            "uncertainty_level": decision.uncertainty,
            "current_task": decision.task_refinement,
        }

    # ============================================================
    #  Agent Node — uses PromptEngine
    # ============================================================

    def _create_agent_node(self, agent_def: AgentDefinition):
        """Factory for agent execution nodes."""

        async def agent_node(state: SwarmState) -> dict:
            task = state.get("current_task", "")
            logger.info(f"🤖 Agent [{agent_def.name}] working on: {task[:80]}")

            # Build prompt via PromptEngine
            system_prompt = self.prompt_engine.build_agent_prompt(
                agent_name=agent_def.name,
                task=task,
                rag_context="",         # TODO: inject RAG results
                memory_context="",      # TODO: inject memory
                tools_available=[t.__name__ if callable(t) else str(t) for t in agent_def.tools],
            )

            # Get the appropriate LLM for this agent
            llm = self._get_llm_for_agent(agent_def)

            # Invoke
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                *state["messages"]
            ])

            return {
                "messages": [response],
                "agent_outputs": {agent_def.name: response.content},
            }

        return agent_node

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

        # Invoke LLM for quality check
        response = await self._default_llm.ainvoke([
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

        return {
            "reflection_count": reflection_count,
            "next_step": next_step,
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
        }

        # Execute the graph
        final_state = await self._graph.ainvoke(initial_state)
        return final_state
