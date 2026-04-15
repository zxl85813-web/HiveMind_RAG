import asyncio
import json
import uuid
import random
from typing import Annotated, Any, Callable, Literal, TypedDict, Coroutine

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from loguru import logger

from app.agents.agentic_search import SEARCH_TOOLS
from app.agents.bus import get_agent_bus
from app.agents.compactor import ContextCompactor
from app.agents.llm_router import LLMRouter
from app.agents.memory import SharedMemoryManager
from app.agents.tools import NATIVE_TOOLS
from app.core.algorithms.routing import vector_agent_router
from app.core.config import settings
from app.services.cache_service import CacheService
from app.core.token_service import TokenService

# [RULE-B001]: Extracted Imports
from app.agents.schemas import SwarmState, AgentDefinition, RoutingDecision, ReflectionResult, ModelTier
from app.agents.scopes import ScopedStateView
from app.agents.parsers import SwarmParser
from app.agents.nodes.reflection import reflection_node
from app.agents.nodes.supervisor import supervisor_node
from app.agents.nodes.agent import create_agent_node
from app.agents.nodes.parallel import parallel_node, consensus_node
from app.agents.nodes.retrieval import retrieval_node
from app.agents.nodes.utils import platform_action_node, reflection_decision_node


class SwarmOrchestrator:
    """
    The central coordinator for the Agent Swarm.
    Extracted internal logic to specialized nodes and utilities for RULE-B001 compliance.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}
        self._graph = None
        self._background_tasks: set[asyncio.Task[Any]] = set()

        self.router = LLMRouter()
        self.memory = SharedMemoryManager()
        self._prompt_engine = None
        self._retriever = None

        from app.agents.mcp_manager import MCPManager
        self.mcp = MCPManager()

        from app.skills.registry import SkillRegistry
        self.skills = SkillRegistry()

        from app.agents.engine import AgentEngine
        self.engine = AgentEngine(self)

        from app.agents.tool_index import ToolIndex, set_tool_index
        self.tool_index = ToolIndex(list(NATIVE_TOOLS))
        set_tool_index(self.tool_index)

        self.bus = get_agent_bus()

        self.compactor = ContextCompactor(
            llm=self.router.get_model(tier=ModelTier.SIMPLE),
            threshold_tokens=int(settings.CONTEXT_WINDOW_LIMIT * settings.BUDGET_HISTORY_RATIO)
        )

        self._initialized = False
        self._init_lock = asyncio.Lock()
        logger.info("🐝 SwarmOrchestrator initialized")

    async def ensure_initialized(self):
        """Ensure MCP, Tool Index, and Graph are stable."""
        if self._initialized: return
        async with self._init_lock:
            if not self._initialized:
                await self.mcp.load_config(settings.MCP_SERVERS_CONFIG_PATH)
                await self.mcp.connect_all()
                await self.tool_index.initialize_embeddings()
                await self.build_graph()
                self._initialized = True

    @property
    def prompt_engine(self):
        if self._prompt_engine is None:
            from app.prompts.engine import prompt_engine
            self._prompt_engine = prompt_engine
        return self._prompt_engine

    def register_agent(self, agent: AgentDefinition) -> None:
        if not agent.model_hint:
            agent.model_hint = self.prompt_engine.get_model_hint(agent.name)
        self._agents[agent.name] = agent
        if agent.description:
            vector_agent_router.register_agent(agent.name, agent.description)

    async def build_graph(self) -> None:
        """Build the LangGraph StateGraph from registered agents."""
        workflow = StateGraph(SwarmState)
        
        # Nodes
        workflow.add_node("pre_processor", self._pre_processor_node)
        workflow.add_node("retrieval", self._retrieval_node)
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("parallel_worker", self._parallel_node)
        workflow.add_node("consensus", self._consensus_node)
        workflow.add_node("reflection", self._reflection_node)
        workflow.add_node("platform_action", self._platform_action_node)
        workflow.add_node("reflection_decision", self._reflection_decision_node)
        
        for name, agent_def in self._agents.items():
            workflow.add_node(name, self._create_agent_node(agent_def))

        # Edges
        workflow.set_entry_point("pre_processor")
        workflow.add_conditional_edges("pre_processor", lambda s: s["next_step"], {"supervisor": "supervisor", "FINISH": END})
        workflow.add_edge("retrieval", "supervisor")
        workflow.add_edge("platform_action", END)
        
        workflow.add_conditional_edges("supervisor", lambda s: s["next_step"], {
            **{name: name for name in self._agents},
            "retrieval": "retrieval",
            "parallel": "parallel_worker",
            "FINISH": END,
            "REFLECTION": "reflection",
            "PLATFORM_ACTION": "platform_action",
        })
        
        for name in self._agents:
            workflow.add_edge(name, "reflection_decision")
            
        workflow.add_conditional_edges("reflection_decision", lambda s: s["next_step"], {
            "REFLECTION": "reflection", "FINISH": END, "supervisor": "supervisor"
        })
        
        workflow.add_conditional_edges("reflection", self._route_after_reflection, {"supervisor": "supervisor", "FINISH": END, "retrieval": "retrieval"})
        workflow.add_edge("parallel_worker", "consensus")
        workflow.add_edge("consensus", "reflection_decision")

        # Persistence
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            import sqlite3
            conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
        except Exception as e:
            checkpointer = MemorySaver()
            logger.warning(f"Persistence fallback to Memory: {e}")

        self._graph = workflow.compile(checkpointer=checkpointer)

    async def _pre_processor_node(self, state: SwarmState) -> dict:
        """Prefetch, Cache, and A/B logic."""
        messages = state.get("messages", [])
        original_query = state.get("original_query", "")

        cached = await CacheService.get_cached_response(original_query)
        if cached:
            return {"messages": [AIMessage(content=cached["content"])], "next_step": "FINISH"}

        variant = state.get("execution_variant") or ("react" if random.random() < 0.5 else "monolithic")
        
        # Adaptive Budget
        complexity = (3 if len(original_query) > 50 else 0) + (4 if any(w in original_query.lower() for w in ["analyze", "audit", "verify"]) else 0)
        budget = 8 if complexity >= 4 else 4
        
        return {"next_step": "supervisor", "execution_variant": variant, "reasoning_budget": budget}

    # Delegation to extracted nodes
    async def _supervisor_node(self, state: SwarmState) -> dict: return await supervisor_node(self, state)
    async def _parallel_node(self, state: SwarmState) -> dict: return await parallel_node(self, state)
    async def _consensus_node(self, state: SwarmState) -> dict: return await consensus_node(self, state)
    async def _reflection_node(self, state: SwarmState) -> dict: return await reflection_node(self, state)
    async def _retrieval_node(self, state: SwarmState) -> dict: return await retrieval_node(self, state)
    async def _platform_action_node(self, state: SwarmState) -> dict: return await platform_action_node(self, state)
    async def _reflection_decision_node(self, state: SwarmState) -> dict: return await reflection_decision_node(self, state)
    
    def _create_agent_node(self, agent_def: AgentDefinition): return create_agent_node(self, agent_def)
    
    def _route_after_reflection(self, state: SwarmState) -> Literal["supervisor", "FINISH", "retrieval"]:
        if state.get("reflection_count", 0) > 5: return "FINISH"
        step = state.get("next_step")
        if step in ["FINISH", "retrieval", "supervisor"]:
            return step
        return "supervisor"

    async def invoke(self, user_message: str, conversation_id: str = "default") -> dict:
        await self.ensure_initialized()
        config = {"configurable": {"thread_id": conversation_id}}
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "original_query": user_message,
            "conversation_id": conversation_id,
            "next_step": "pre_processor",
            "reflection_count": 0,
            "agent_outputs": {}
        }
        return await self._graph.ainvoke(initial_state, config=config)

    async def invoke_stream(self, user_message: str, context: dict, conversation_id: str = "default"):
        """Stream orchestration steps via LangGraph (Reference: REQ-015)."""
        await self.ensure_initialized()
        config = {"configurable": {"thread_id": conversation_id}}
        
        # Merge context into initial state if needed
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "original_query": user_message,
            "conversation_id": conversation_id,
            "next_step": "pre_processor",
            "reflection_count": 0,
            "agent_outputs": {},
            "context_data": context.get("knowledge_base_ids", [])
        }

        async for event in self._graph.astream(initial_state, config=config, stream_mode="updates"):
            yield event

    def get_agents(self) -> dict[str, AgentDefinition]:
        """Return the dictionary of registered agents."""
        return self._agents
