"""
HiveMind Worker Base Class (M4.1.2)

Standardizes the agent lifecycle:
1. init:      Context setup.
2. execute:   Run the task.
3. reflect:   Check if goals were met.
"""

import asyncio
from typing import Any

from loguru import logger

from app.services.agents.protocol import AgentResponse, AgentStatus, AgentTask, BaseAgent
from app.services.llm_gateway import llm_gateway
from app.prompts.dialect import model_dialect
from app.services.agents.review_governance import review_governance


class WorkerAgent(BaseAgent):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Main entry for Agent execution with Tracing (M4.1.4)."""
        import time

        from app.models.observability import TraceStatus as ObsStatus
        from app.services.swarm_observability import record_swarm_span

        start_time = time.time()
        self.status = AgentStatus.EXECUTING
        logger.info(f"Agent {self.name} executing task: {task.id}")

        # 🏎️ L5 Adaptation: Apply Model-Specific Dialect to the instruction
        # We determine the target model based on priority if not overridden
        priority = task.context.get("priority", 2)
        target_model_profile = review_governance.get_optimal_critic(priority)
        target_model = target_model_profile.name.lower().replace(" ", "-")
        
        task.instruction = model_dialect.wrap_instruction(target_model, task.instruction)

        try:
            # 1. Logic Execution — now with Swarm Blackboard access
            output, knowledge, signal = await self._run_logic(task)
            latency_ms = (time.time() - start_time) * 1000

            # 2. Reflection
            self.status = AgentStatus.REFLECTING
            await self._reflect(task, output)

            self.status = AgentStatus.DONE

            # 🔒 3. RECORD TRACE
            if task.swarm_trace_id:
                asyncio.create_task(record_swarm_span(
                    trace_id=task.swarm_trace_id,
                    agent_name=self.name,
                    instruction=task.instruction,
                    output=str(output),
                    latency_ms=latency_ms,
                    status=ObsStatus.SUCCESS
                ))

            return AgentResponse(
                task_id=task.id,
                output=str(output),
                new_knowledge=knowledge or {},
                signal=signal or {},
                status=self.status
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.exception(f"Agent {self.name} FAILED: {e}")
            self.status = AgentStatus.FAILED

            if task.swarm_trace_id:
                asyncio.create_task(record_swarm_span(
                    trace_id=task.swarm_trace_id,
                    agent_name=self.name,
                    instruction=task.instruction,
                    output=f"Error: {e}",
                    latency_ms=latency_ms,
                    status=ObsStatus.FAILED
                ))

            return AgentResponse(task_id=task.id, output=f"Internal Error: {e}", status=self.status)

    async def _run_logic(self, task: AgentTask) -> tuple[Any, dict[str, Any], dict[str, Any]]:
        """Worker's specialized logic. Returns (Output, Knowledge, Signal)."""
        raise NotImplementedError("Subclasses must implement _run_logic.")

    async def _reflect(self, task: AgentTask, output: Any) -> None:
        """
        L5 Node-Level Reflection: Self-Correction phase using a fast model.
        Verifies if the output satisfies the original instruction checkpoints.
        """
        logger.debug(f"Agent {self.name} performing structured reflection on output...")
        
        # Use a Tier 1 (Fast) model for reflection to keep latency low
        reflection_prompt = f"""
        Review the following AI agent output against the given instruction.
        
        ### Instruction:
        {task.instruction}
        
        ### Output to Check:
        {str(output)[:2000]}
        
        Check if the output:
        1. Correctly follows the instruction logic.
        2. Maintains valid formatting (JSON/Code).
        3. Doesn't contain 'hallucinated' errors or placeholders.
        
        Return ONLY valid JSON:
        {{
          "is_valid": true | false,
          "reason": "summary of findings",
          "improvement_suggestion": "optional"
        }}
        """
        
        try:
            res = await llm_gateway.call_tier(
                tier=1, 
                prompt=reflection_prompt, 
                system_prompt="You are a node-level quality critic.",
                response_format={"type": "json_object"}
            )
            import json
            critique = json.loads(res.content)
            
            if not critique.get("is_valid", True):
                logger.warning(f"⚠️ Agent {self.name} node-reflection failed: {critique.get('reason')}")
                # We could set a signal here for the Supervisor to see
                task.context["node_reflection_failure"] = critique.get("reason")
            else:
                logger.info(f"✅ Agent {self.name} node-reflection passed.")
        except Exception as e:
            logger.error(f"Node reflection error for {self.name}: {e}")
            # [SHELL: M4.1.4] Fail-safe placeholder for reflection errors to prevent deadlock. Full recovery required for Phase 5.
            pass
