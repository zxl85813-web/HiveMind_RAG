"""
Agent Streaming Engine — handles real-time execution flows for Swarm Agents.
Inspired by Claude Code's QueryEngine AsyncGenerator pattern.
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import SystemMessage, ToolMessage
from loguru import logger

from app.utils.env_context import get_env_context


@dataclass
class AgentEvent:
    """Unified event for real-time tracking of agent progress."""
    type: str  # "thinking" | "tool_call" | "tool_result" | "text" | "error" | "done"
    agent_name: str
    content: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "agent": self.agent_name,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": time.time()
        }

class AgentEngine:
    """
    CC-inspired Agent Engine that treats the reasoning loop as a stream.
    
    This class bridges the static LangGraph StateGraph nodes with real-time SSE/WS requirements.
    It performs the iterative Think-Act-Observe loop and yields events at each step.
    """

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator # SwarmOrchestrator reference

    async def execute_agent_stream(
        self,
        agent_def: Any,
        llm: Any,
        available_tools: list[Any],
        system_prompt: str,
        state: dict,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Executes an agent's logic as an asynchronous stream.
        
        Yields:
            AgentEvent for real-time tracking.
        """
        agent_name = agent_def.name
        env_context = get_env_context()
        full_system_prompt = f"{system_prompt}\n\n{env_context}"
        
        messages = [SystemMessage(content=full_system_prompt)]
        messages.extend(state.get("messages", []))

        # Adaptive budget
        max_steps = state.get("reasoning_budget") or 5

        session_thinking_times = []
        session_tool_times = []
        current_messages = list(messages)
        final_content = ""

        logger.info(f"🌊 [Streaming Engine] Starting execution for {agent_name}")

        try:
            for step in range(max_steps):
                # 1. THINK
                # CC-inspired: first event is always a progress indicator
                yield AgentEvent(
                    type="progress",
                    agent_name=agent_name,
                    content=f"Step {step+1}: Analyzing task..."
                )

                t0 = time.monotonic()
                # Use ainvoke for streaming response if we want token-level streaming later,
                # but for now we focus on the Think-Act cycle.
                response = await llm.ainvoke(current_messages)
                think_ms = (time.monotonic() - t0) * 1000
                session_thinking_times.append(think_ms)

                # Broadly thinking event
                yield AgentEvent(
                    type="thinking",
                    agent_name=agent_name,
                    content=str(response.content),
                    metadata={"think_ms": think_ms, "step": step + 1}
                )

                current_messages.append(response)

                if not response.tool_calls:
                    final_content = response.content
                    yield AgentEvent(type="text", agent_name=agent_name, content=str(final_content))
                    break

                # 2. ACT
                tool_names = [tc["name"] for tc in response.tool_calls]
                yield AgentEvent(
                    type="tool_call",
                    agent_name=agent_name,
                    content=f"Calling tools: {', '.join(tool_names)}",
                    metadata={"tool_calls": response.tool_calls}
                )

                # Parallel dispatch
                tool_tasks = []
                for tc in response.tool_calls:
                    tool_tasks.append(self.orchestrator._execute_tool(
                        tc, available_tools, agent_name, state
                    ))

                tool_results = await asyncio.gather(*tool_tasks)

                # 3. OBSERVE
                for i, (res_val, duration) in enumerate(tool_results):
                    tc = response.tool_calls[i]
                    session_tool_times.append(duration)

                    yield AgentEvent(
                        type="tool_result",
                        agent_name=agent_name,
                        content=res_val,
                        metadata={"tool": tc["name"], "duration_ms": duration}
                    )

                    current_messages.append(ToolMessage(tool_call_id=tc["id"], content=res_val))

            # Final Cleanup
            yield AgentEvent(type="done", agent_name=agent_name, content="Execution completed.")

            # Calculate state update for LangGraph
            new_msgs_count = len(current_messages) - len(messages)
            new_messages = current_messages[-new_msgs_count:] if new_msgs_count > 0 else []

            # 🛠️ Important: Yield the final result state as a special event
            # This allows the consumer to pick it up at the end of the generator.
            yield AgentEvent(
                type="result",
                agent_name=agent_name,
                content="final_state",
                metadata={
                    "messages": new_messages,
                    "agent_outputs": {agent_name: str(final_content)},
                    "thinking_time_ms": session_thinking_times,
                    "tool_time_ms": session_tool_times
                }
            )

        except Exception as e:
            logger.error(f"❌ [Streaming Engine] Error in {agent_name} loop: {e}")
            yield AgentEvent(type="error", agent_name=agent_name, content=str(e))

    async def stream_and_broadcast(self, conversation_id: str, user_id: str, *args, **kwargs):
        """
        Helper that consumes the generator and broadcasts to WebSocket.
        Returns the final state update dict.
        """
        from app.agents.bus import get_agent_bus
        from app.services.ws_manager import ws_manager

        bus = get_agent_bus()
        final_state = {}

        async for event in self.execute_agent_stream(*args, **kwargs):
            # 1. WS Broadcast (User visibility)
            payload = event.to_dict()
            payload["conversation_id"] = conversation_id

            if user_id:
                asyncio.create_task(ws_manager.send_to_user(user_id, {"type": "swarm_event", "data": payload}))

            # 2. Bus Publish (Peer visibility - OPT-3)
            # This allows other agents to "hear" what this agent is doing in real-time.
            asyncio.create_task(bus.publish(
                topic="swarm_events",
                sender=event.agent_name,
                payload=payload
            ))

            # 3. Capture result at the end
            if event.type == "result":
                final_state = event.metadata

        return final_state
