from typing import Any

from loguru import logger

from app.services.agents.protocol import AgentTask
from app.services.agents.worker import WorkerAgent
from app.services.llm_gateway import llm_gateway


class ReviewerAgent(WorkerAgent):
    """
    Expert in 'Cross-Viewpoint' Critique and Logic Verification.
    Its goal is to find bugs, security risks, or inconsistencies in other agents' outputs.
    """

    def __init__(self):
        super().__init__(
            name="HVM-Reviewer",
            description="Specialized in code audit, logic validation, and cross-viewpoint critical review. Guaranteed to find gaps."
        )

    async def _run_logic(self, task: AgentTask) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Perform a critical review of the current blackboard state."""
        logger.info(f"ReviewerAgent auditing: {task.instruction}")

        # 🧪 Swarm Advantage: Access the BLACKBOARD to find targets for review
        targets = []
        if task.blackboard:
            # Review all previous outputs
            targets = [f"--- Task {tid} ---\n{output}" for tid, output in task.blackboard.items()]

        blackboard_str = "\n".join(targets)

        system_prompt = f"""
        You are the HiveMind Reviewer Agent. 
        Your goal is to be hyper-critical. Find issues (logic, security, style) in the following Swarm Blackboard.
        
        Objective of the whole Swarm: {task.description}
        
        Shared Knowledge (Blackboard):
        {blackboard_str}
        
        Audit Rules:
        1. Identify exactly which task you are critiquing.
        2. Provide 'CONTRARY VIEWPOINTS' (e.g., 'Agent T1 assumed X, but if Y happens, it fails').
        3. Rate the overall risk (Low/Medium/High).
        """

        response = await llm_gateway.call_tier(
            tier=3, # Reasoning Tier
            prompt=task.instruction,
            system_prompt=system_prompt
        )

        # 💡 Return Intelligence Signal
        # If we find a critical issue, we SIGNAL it to the Supervisor
        signal = {"status": "REVIEWED"}
        if "HIGH RISK" in response.content.upper() or "ERROR" in response.content.upper():
            signal["requires_replan"] = True
            signal["critical_failure"] = True

        return response.content, {"risk_level": "captured"}, signal
