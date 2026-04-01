"""
HiveMind Agent Swarm Protocol (v1.0)

Definitions for:
- AgentState: Current knowledge and status of an agent.
- BaseAgent: Interface for all swarm members.
- AgentTask: A unit of work assigned to an agent.
"""

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    DONE = "done"
    FAILED = "failed"


class AgentTask(BaseModel):
    id: str
    swarm_trace_id: str | None = None  # 🔗 Trace link (M4.1.4)
    description: str
    instruction: str
    context: dict[str, Any] = Field(default_factory=dict)
    # 🧠 Swarm Advantage: Access to the global blackboard (shared context from other agents)
    blackboard: dict[str, Any] = Field(default_factory=dict)
    assigned_to: str | None = None


class AgentResponse(BaseModel):
    task_id: str
    output: str
    new_knowledge: dict[str, Any] = Field(default_factory=dict)
    # 💡 Intelligence Signal: Allows agent to influence the Swarm's direction
    signal: dict[str, Any] = Field(default_factory=dict)
    status: AgentStatus


@runtime_checkable
class BaseAgent(Protocol):
    name: str
    description: str

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Execute a task and return a response."""
        ...
