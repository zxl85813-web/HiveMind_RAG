"""
Swarm Observability Service (M4.1.4)

Records the lifecycle of a multi-agent HiveMind Swarm.
- Start SwarmTrace (Supervisor triage)
- Record SwarmSpan (Worker execution)
- Finalize SwarmTrace
"""

import uuid
import time
from datetime import datetime
from typing import Any, List
from loguru import logger
from app.core.database import async_session_factory
from app.models.observability import SwarmTrace, SwarmSpan, TraceStatus


async def start_swarm_trace(query: str, user_id: str | None = None) -> str:
    """Initialize a high-level swarm trace."""
    trace_id = str(uuid.uuid4())
    async with async_session_factory() as session:
        trace = SwarmTrace(
            id=trace_id,
            user_id=user_id,
            query=query,
            status=TraceStatus.RUNNING
        )
        session.add(trace)
        await session.commit()
    return trace_id


async def record_swarm_triage(trace_id: str, reasoning: str) -> None:
    """Update triage reasoning for a swarm trace."""
    async with async_session_factory() as session:
        trace = await session.get(SwarmTrace, trace_id)
        if trace:
            trace.triage_reasoning = reasoning
            session.add(trace)
            await session.commit()


async def record_swarm_span(
    trace_id: str,
    agent_name: str,
    instruction: str,
    output: str | None = None,
    latency_ms: float = 0.0,
    status: TraceStatus = TraceStatus.SUCCESS
) -> str:
    """Write an entry for a single agent's execution."""
    span_id = str(uuid.uuid4())
    async with async_session_factory() as s:
        span = SwarmSpan(
            id=span_id,
            swarm_trace_id=trace_id,
            agent_name=agent_name,
            instruction=instruction,
            output=output,
            latency_ms=latency_ms,
            status=status
        )
        s.add(span)
        await s.commit()
    return span_id


async def finalize_swarm_trace(trace_id: str, status: TraceStatus = TraceStatus.SUCCESS) -> None:
    """Mark a swarm request as complete."""
    async with async_session_factory() as s:
        trace = await s.get(SwarmTrace, trace_id)
        if trace:
            trace.status = status
            s.add(trace)
            await s.commit()
