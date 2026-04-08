from typing import Any

from loguru import logger

from app.services.agents.protocol import AgentTask
from app.services.agents.worker import WorkerAgent
from app.services.llm_gateway import llm_gateway


class ReviewerAgent(WorkerAgent):
    """
    Expert in 'Cross-Viewpoint' Critique and Logic Verification.
    Its goal is to find bugs, security risks, or inconsistencies in other agents' outputs.
    Outputs STRUCTURED JSON so that signals are reliable (not brittle string matching).
    """

    def __init__(self):
        super().__init__(
            name="HVM-Reviewer",
            description="Specialized in code audit, logic validation, and cross-viewpoint critical review. Guaranteed to find gaps."
        )

    async def _run_logic(self, task: AgentTask) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Perform a structured critical review of the current blackboard state."""
        logger.info(f"ReviewerAgent auditing: {task.instruction}")

        # 🧪 Swarm Advantage: Access the BLACKBOARD to find targets for review
        targets = []
        if task.blackboard:
            targets = [f"--- Task {tid} ---\n{output}" for tid, output in task.blackboard.items()]

        blackboard_str = "\n".join(targets)

        system_prompt = f"""
        You are the HiveMind Reviewer Agent.
        Your goal is to be hyper-critical. Audit the Swarm Blackboard below for issues.

        Objective of the whole Swarm: {task.description}

        Shared Knowledge (Blackboard):
        {blackboard_str}

        Audit Rules:
        1. Identify exactly which task you are critiquing.
        2. Provide 'CONTRARY VIEWPOINTS' (e.g., 'Agent T1 assumed X, but if Y happens, it fails').
        3. Rate the overall risk strictly using: "LOW", "MEDIUM", or "HIGH".
        4. Set 'requires_replan' to true ONLY if a HIGH-risk issue blocks objective completion.

        Return ONLY valid JSON:
        {{
          "risk_level": "LOW" | "MEDIUM" | "HIGH",
          "findings": ["specific finding 1", "specific finding 2"],
          "requires_replan": true | false,
          "summary": "one-line verdict"
        }}
        """

        response = await llm_gateway.call_tier(
            tier=3,  # Reasoning Tier
            prompt=task.instruction,
            system_prompt=system_prompt,
            response_format={{"type": "json_object"}},
        )

        # 💡 Parse structured signal — no brittle string matching
        import json

        try:
            audit_data = json.loads(response.content)
        except Exception:
            audit_data = {"risk_level": "UNKNOWN", "requires_replan": False, "findings": [], "summary": response.content}

        risk_level = audit_data.get("risk_level", "UNKNOWN").upper()
        requires_replan = audit_data.get("requires_replan", False)

        signal: dict[str, Any] = {
            "status": "REVIEWED",
            "risk_level": risk_level,
            "findings": audit_data.get("findings", []),
        }
        if requires_replan or risk_level == "HIGH":
            signal["requires_replan"] = True
            signal["critical_failure"] = True
            logger.warning(f"🚨 Reviewer flagged HIGH risk: {audit_data.get('summary', '')}")
        else:
            logger.info(f"✅ Reviewer verdict: {risk_level} | {audit_data.get('summary', '')}")

        return response.content, {"risk_level": risk_level}, signal
