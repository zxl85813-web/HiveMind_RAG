from typing import Any

from loguru import logger

from app.services.agents.protocol import AgentTask
from app.services.agents.worker import WorkerAgent
from app.services.llm_gateway import llm_gateway
from app.services.agents.review_governance import review_governance
from app.prompts.dialect import model_dialect


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

        # 🚦 L5 Governance: Select Optimal Critic based on Priority
        priority = task.context.get("priority", 2)
        optimal_critic = review_governance.get_optimal_critic(priority)
        model_name = optimal_critic.name.lower().replace(" ", "-")
        governance_context = review_governance.get_governance_context(model_name)

        # 🏎️ Adaptive Dialect: Wrap system and instruction correctly for the target model
        dialect_instruction = model_dialect.wrap_instruction(model_name, task.instruction)
        output_hook = model_dialect.get_output_format_hook(model_name)

        system_prompt = f"""
        You are the HiveMind Reviewer Agent.
        Your goal is to be hyper-critical. Audit the Swarm Blackboard below for issues.

        {governance_context}

        Objective of the whole Swarm: {task.description}
        Priority Level: {priority}

        Shared Knowledge (Blackboard):
        {blackboard_str}

        Audit Rules:
        1. Identify exactly which task you are critiquing.
        2. Provide 'CONTRARY VIEWPOINTS' based on your model strengths.
        3. Acknowledge if the issue justifies the cost of higher-tier models or multi-swarm debate.
        4. Rate the overall risk strictly using: "LOW", "MEDIUM", or "HIGH".
        5. Set 'requires_replan' to true ONLY if a HIGH-risk issue blocks objective completion.

        {output_hook}

        Return a valid JSON object matching this schema:
        {{
          "risk_level": "LOW" | "MEDIUM" | "HIGH",
          "findings": ["specific finding 1", "specific finding 2"],
          "requires_replan": true | false,
          "summary": "one-line verdict",
          "economic_analysis": "brief note on whether this review tier was appropriate for the risk",
          "confidence": 0.0-1.0
        }}
        """

        response = await llm_gateway.call_tier(
            tier=3,  # Reasoning Tier
            prompt=dialect_instruction,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
            model_override=model_name # Fallback to mapped name
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
        # 🏛️ L4/L5 Learning Loop: Log Granular Experience for the Learner
        experience_meta = {
            "query": task.description,
            "priority": priority,
            "model": optimal_critic.name,
            "risk_level": risk_level,
            "cost_input": optimal_critic.cost_per_1m_input,
            "summary": audit_data.get("summary", ""),
            "confidence_score": audit_data.get("confidence", 0.8), # Default if not returned
            "trace_id": task.swarm_trace_id
        }
        logger.bind(action="reviewer_experience", meta=experience_meta).info(f"Reviewer verdict: {risk_level} | {audit_data.get('summary', '')}")

        if requires_replan or risk_level == "HIGH":
            signal["requires_replan"] = True
            signal["critical_failure"] = True
            logger.warning(f"🚨 Reviewer flagged HIGH risk: {audit_data.get('summary', '')}")
        else:
            logger.info("✅ Reviewer verdict recorded.")

        return response.content, {"risk_level": risk_level}, signal
