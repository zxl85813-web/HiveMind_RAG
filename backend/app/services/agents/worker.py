"""
HiveMind Worker Base Class (M4.1.2)

Standardizes the agent lifecycle:
1. init:      Context setup.
2. execute:   Run the task.
3. reflect:   Check if goals were met.
"""

from typing import Any, List
import asyncio
from app.services.agents.protocol import BaseAgent, AgentTask, AgentResponse, AgentStatus
from loguru import logger


class WorkerAgent(BaseAgent):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Main entry for Agent execution with Tracing (M4.1.4)."""
        import time
        from app.services.swarm_observability import record_swarm_span
        from app.models.observability import TraceStatus as ObsStatus

        start_time = time.time()
        self.status = AgentStatus.EXECUTING
        logger.info(f"Agent {self.name} executing task: {task.id}")

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
        """Self-Correction / Verification phase."""
        # Basic sanity check. Expanded in M4.1.4.
        logger.debug(f"Agent {self.name} reflecting on output length: {len(str(output))}")
        pass
