"""
Native LangGraph Ingestion Swarm (V3 Architecture).

This defines a state-driven, non-linear orchestration for processing
complex documents (PDF, Code, Excel) using a swarm of specialized Agents.

Replaces: app.batch.ingestion.executor.IngestionExecutor
"""

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger

from app.batch.ingestion.core import ParserRegistry
from app.core.database import async_session_factory
from app.core.telemetry.tracer import LightweightRedisTracer
from app.services.ingestion.swarm.assembler import SwarmAssembler
from app.services.security_service import SecurityService

# --- Swarm State Definition ---


class IngestionState(TypedDict):
    """
    The blackboard state for the Ingestion Swarm.
    """

    # Trace info
    trace_id: str
    kb_id: str
    file_path: str

    # Content extraction storage
    raw_text: str
    sections: list[dict[str, Any]]

    # Processing Metadata (Confidence and Quality)
    confidence_score: float
    is_sensitive: bool
    audit_verdict: str  # PASS, REVISE, HITL

    # Routing control
    next_step: str
    errors: list[str]

    # Internal agent messages for reasoning
    messages: Annotated[list[BaseMessage], add_messages]


# --- Swarm Orchestrator Class ---


class IngestionOrchestrator:
    """
    Orchestrates the data ingestion process using a Native LangGraph Swarm.
    """

    def __init__(self, trace_id: str, kb_id: str):
        self.trace_id = trace_id
        self.kb_id = kb_id
        self.tracer = LightweightRedisTracer(trace_id=trace_id, agent_name="IngestionSwarm")
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Constructs the non-linear processing graph."""
        workflow = StateGraph(IngestionState)

        # 1. Add Processing Nodes
        workflow.add_node("parser_agent", self._parser_node)
        workflow.add_node("security_agent", self._security_node)
        workflow.add_node("critic_agent", self._critic_node)
        workflow.add_node("assembler_node", self._assembler_node)

        # 2. Define Edges (Non-linear flow)
        workflow.set_entry_point("parser_agent")

        # Parser -> Security (Always scan for PII/BSI)
        workflow.add_edge("parser_agent", "security_agent")

        # Security -> Critic (Evaluate quality and extraction completeness)
        workflow.add_edge("security_agent", "critic_agent")

        # Critic decides:
        # - High quality -> Assemble & Vectorize
        # - Low quality/Ambiguous -> HitL Queue (End Early)
        # - Recoverable Error -> Parser Retry (Loop)
        workflow.add_conditional_edges(
            "critic_agent",
            self._route_critic_decision,
            {
                "assemble": "assembler_node",
                "retry": "parser_agent",
                "hitl": END,  # Will be flagged in the state for the fallback queue
            },
        )

        workflow.add_edge("assembler_node", END)

        return workflow.compile()

    # --- Node Implementations ---

    async def _parser_node(self, state: IngestionState) -> dict[str, Any]:
        """Specialized Agent for extracting content from various formats."""
        file_path = state["file_path"]
        logger.info(f"🤖 [Swarm] ParserAgent extracting: {file_path}")

        # 1. Identify best-fit parser
        parser_cls = ParserRegistry.get_parser_for_file(file_path)
        if not parser_cls:
            return {"audit_verdict": "hitl", "errors": ["No suitable parser found"]}

        # 2. Execute parsing
        parser = parser_cls()
        resource = await parser.parse(file_path)

        return {
            "raw_text": resource.raw_text,
            "sections": [s.model_dump() for s in resource.sections],
            "next_step": "scan",
        }

    async def _security_node(self, state: IngestionState) -> dict[str, Any]:
        """PII / Sensitive data scanning agent."""
        logger.info("🛡️ [Swarm] SecurityAgent scanning for sensitive patterns...")

        async with async_session_factory() as session:
            # Apply real desensitization to raw text
            redacted_text, applied_records = await SecurityService.apply_desensitization(
                state.get("raw_text", ""), db=session, doc_id=state.get("file_path")
            )

            # Update state with redacted content
            return {"raw_text": redacted_text, "is_sensitive": len(applied_records) > 0}

    async def _critic_node(self, state: IngestionState) -> dict[str, Any]:
        """Quality control agent that evaluates if the extraction is usable."""
        logger.info("⚖️ [Swarm] CriticAgent evaluating extraction quality...")

        # Simulate check
        if len(state["raw_text"]) < 5:
            return {"audit_verdict": "retry", "errors": ["Text too short"]}

        return {"audit_verdict": "PASS", "confidence_score": 0.98}

    async def _assembler_node(self, state: IngestionState) -> dict[str, Any]:
        """Final node: Contextual chunking and Vector synchronization."""
        logger.info("🧩 [Swarm] KnowledgeAssembler starting AssemblerService...")

        # Restore real chunking & vectorization
        result = await SwarmAssembler.process_and_vectorize(
            kb_id=self.kb_id,
            doc_id=state.get("file_path"),
            raw_text=state.get("raw_text", ""),
            sections=state.get("sections", []),
        )

        return {"next_step": "completed", "assembler_result": result}

    # --- Routing Logic ---

    def _route_critic_decision(self, state: IngestionState) -> Literal["assemble", "retry", "hitl"]:
        verdict = state.get("audit_verdict", "PASS")
        if verdict == "PASS" or verdict == "assemble":
            return "assemble"
        elif (verdict == "retry" or verdict == "REVISE") and len(state.get("errors", [])) < 3:
            return "retry"
        return "hitl"

    # --- Execution Entrypoint ---

    async def run(self, file_path: str) -> dict[str, Any]:
        """Execute the swarm for a single file."""
        initial_state: IngestionState = {
            "trace_id": self.trace_id,
            "kb_id": self.kb_id,
            "file_path": file_path,
            "raw_text": "",
            "sections": [],
            "confidence_score": 0.0,
            "is_sensitive": False,
            "audit_verdict": "",
            "next_step": "",
            "errors": [],
            "messages": [],
        }

        result = await self._graph.ainvoke(initial_state)
        return result
