"""
HiveMind Code Agent (Specialized Worker)

Purpose: Generates, refines, and analyzes code based on instructions.
Integration: High-fidelity code synthesis (ClawRouter Tier 3).
"""

from typing import Any

from loguru import logger

from app.services.agents.protocol import AgentTask
from app.services.agents.worker import WorkerAgent
from app.services.llm_gateway import llm_gateway


class CodeAgent(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="CodeAgent",
            description="Expert in Python, TypeScript and Systems Architecture. Generates production-grade code."
        )

    async def _run_logic(self, task: AgentTask) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Worker's specialized logic: LLM-based Code Synthesis with Swarm Context."""
        logger.info(f"CodeAgent generating code for task: {task.instruction}")

        # 🧠 Swarm Advantage: Incorporate research results as direct context
        context_enrichment = ""
        if task.blackboard:
            context_enrichment = "\nKnowledge Blackboard (Inputs from other agents):\n"
            for k, v in task.blackboard.items():
                context_enrichment += f"--- Result from {k} ---\n{v}\n"

        # Dispatch to LLM (ClawRouter Tier 3 - COMPLEX_MODEL)
        system_prompt = f"""
        You are the HiveMind Code Agent.
        Your task: {task.instruction}
        {context_enrichment}
        
        Provide high-fidelity, clean, commented code.
        """

        # 1. Execution phase
        response = await llm_gateway.call_tier(
            tier=3, # COMPLEX_MODEL
            prompt=task.instruction,
            system_prompt=system_prompt
        )

        # 2. Reflection / Formatting
        code_output = f"```python\n{response.content}\n```"

        return code_output, {"language": "python"}, {"model": response.metadata.get("model")}
