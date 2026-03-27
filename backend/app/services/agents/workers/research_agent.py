"""
HiveMind Research Agent (Specialized Worker)

Purpose: Retrieves and summarizes information from the HiveMind Knowledge Base.
Integration: Calls RAGGateway for high-fidelity retrieval.
"""

from typing import Any, Tuple
from app.services.agents.worker import WorkerAgent
from app.services.agents.protocol import AgentTask
from app.services.rag_gateway import RAGGateway
from app.services.llm_gateway import llm_gateway
from loguru import logger


class ResearchAgent(WorkerAgent):
    def __init__(self, kb_ids: list[str] | None = None):
        super().__init__(
            name="ResearchAgent",
            description="Expert in retrieving, synthesizing and verifying knowledge from the corporate KB."
        )
        self.kb_ids = kb_ids or []
        self.gw = RAGGateway()

    async def _run_logic(self, task: AgentTask) -> Tuple[str, dict[str, Any], dict[str, Any]]:
        """Worker's specialized logic: RAG-based Research with Collective Intelligence (Blackboard)."""
        logger.info(f"ResearchAgent researching for task: {task.instruction}")
        
        # 🧠 Swarm Advantage: Check what we ALREADY know from other agents (Research-Code collaboration)
        if task.blackboard:
            # Optionally adjust retrieval based on what others found
            logger.debug(f"ResearchAgent utilizing blackboard with {len(task.blackboard)} previous results.")

        # 1. RAG Retrieval
        res = await self.gw.retrieve(
            query=task.instruction, 
            kb_ids=self.kb_ids, 
            user_id="supervisor_system", 
            top_k=8
        )
        
        if not res.fragments:
            return "No relevant information found in knowledge base.", {}, {"status": "NO_RECORDS"}
            
        context_str = "\n".join([f"[{i}] {f.content}" for i, f in enumerate(res.fragments)])
        
        # 2. LLM Synthesis
        # We can now inject findings from OTHER agents to refine our summary
        blackboard_summary = ""
        if task.blackboard:
            blackboard_summary = "\nExisting HiveMind Knowledge:\n" + "\n".join([f"- {k}: {str(v)[:100]}..." for k, v in task.blackboard.items()])

        system_prompt = f"""
        You are the HiveMind Research Agent.
        Your goal is to synthesize the provided research fragments into a clear, concise summary.
        Objective: {task.instruction}
        {blackboard_summary}
        
        Fragments:
        {context_str}
        """
        
        synth_response = await llm_gateway.call_tier(
            tier=2, 
            prompt=f"Synthesize research for: {task.instruction}",
            system_prompt=system_prompt
        )
        
        # 💡 Return Intelligence Signal
        # Example: if we find critical security info, we signal "SECURITY_HINT" 
        doc_ids = list(set([f.metadata.get("document_id") for f in res.fragments]))
        signal = {"found_docs": len(doc_ids)}
        if "security" in synth_response.content.lower():
            signal["requires_audit"] = True

        return synth_response.content, {"doc_ids": doc_ids}, signal
