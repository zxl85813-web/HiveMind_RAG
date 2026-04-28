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

        # 🏗️ Three-Layer Prompt: 使用缓存的 Layer 1+2 作为 system_prompt
        harness_prefix = task.context.get("_harness_system_prefix", "")

        # Layer 3: Hot Context（每次不同，放在 user message）
        from app.sdk.harness.prompt_assembler import build_hot_context

        user_message = build_hot_context(
            task_instruction=task.instruction,
            blackboard=task.blackboard if task.blackboard else None,
        )

        # System Prompt = Layer 1+2（缓存友好）+ Agent 专属指令
        system_prompt = harness_prefix or "You are the HiveMind Code Agent."
        system_prompt += "\n\nProvide high-fidelity, clean, commented code."

        # Dispatch to LLM (ClawRouter Tier 3 - COMPLEX_MODEL)
        response = await llm_gateway.call_tier(
            tier=3,
            prompt=user_message,
            system_prompt=system_prompt
        )

        code_output = f"```python\n{response.content}\n```"

        return code_output, {"language": "python"}, {"model": response.metadata.get("model")}
