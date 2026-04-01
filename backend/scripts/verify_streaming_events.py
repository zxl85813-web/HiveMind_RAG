"""
Verification script for HiveMind Streaming Engine (OPT-2).
Simulates an agent execution and captures real-time WebSocket events.
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure we are in the backend root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock components that are not needed for logic testing
sys.modules['app.services.evaluation.ab_tracker'] = MagicMock()

# Avoid actual DB or heavy service init if possible
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from app.agents.swarm import SwarmOrchestrator, AgentDefinition
from app.agents.engine import AgentEvent
from app.agents.tool_types import hive_tool

class TestStreamingEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # We need to mock several things that might trigger in __init__
        self.orchestrator = SwarmOrchestrator()
        
        # Define a mock tool with metadata
        @hive_tool(is_read_only=True, always_load=True)
        async def mock_test_tool(query: str):
            """A simple tool for testing streaming."""
            return f"Result for: {query}"
        
        # Ensure name is set for the tool (LangChain tools usually have it)
        mock_test_tool.name = "mock_test_tool"
        
        self.test_agent = AgentDefinition(
            name="test_streamer",
            description="Agent for testing streaming events",
            tools=[mock_test_tool]
        )
        self.orchestrator.register_agent(self.test_agent)

    @patch("app.services.ws_manager.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_event_streaming_sequence(self, mock_send):
        """
        Prove that events (progress -> thinking -> tool_call -> tool_result -> done)
        are emitted correctly through the side-channel during LangGraph execution.
        """
        print("\n🚀 Starting Streaming Node Verification...")
        
        # Mock LLM to return a tool call then a final answer
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[
            AIMessage(content="I will call the mock tool.", tool_calls=[{
                "name": "mock_test_tool", 
                "args": {"query": "hello world"},
                "id": "call_1"
            }]),
            AIMessage(content="The tool said hello. Task complete.")
        ])
        # Ensure bind_tools returns self for chaining
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        
        # Patch the internal LLM getter
        self.orchestrator._get_llm_for_agent = MagicMock(return_value=mock_llm)
        
        # Prepare state
        state = {
            "messages": [],
            "current_task": "Test streaming logic.",
            "conversation_id": "test_conv_123",
            "user_id": "test_user_456",
            "reasoning_budget": 5
        }
        
        # 1. Execute the agent node (this is what LangGraph calls)
        node_func = self.orchestrator._create_agent_node(self.test_agent)
        result = await node_func(state)
        
        # 2. Inspect captured WebSocket events
        # ws_manager.send_to_user(user_id, {"type": "swarm_event", "data": payload})
        captured_payloads = [call.args[1] for call in mock_send.call_args_list]
        event_types = [p["data"]["type"] for p in captured_payloads]
        
        print(f"📈 Total events captured: {len(event_types)}")
        for i, etype in enumerate(event_types):
            print(f"  [{i}] {etype} | content='{str(captured_payloads[i]['data']['content'])[:40]}...'")

        # 3. Assertions
        self.assertIn("progress", event_types, "Missing progress event")
        self.assertIn("thinking", event_types, "Missing thinking event")
        self.assertIn("tool_call", event_types, "Missing tool_call event")
        self.assertIn("tool_result", event_types, "Missing tool_result event")
        self.assertIn("done", event_types, "Missing done event")
        self.assertIn("result", event_types, "Missing final result internal event")
        
        # Check payload metadata
        tool_result_event = next(p for p in captured_payloads if p["data"]["type"] == "tool_result")
        self.assertEqual(tool_result_event["data"]["content"], "Result for: hello world")
        self.assertEqual(tool_result_event["data"]["metadata"]["tool"], "mock_test_tool")
        
        print("\n✅ Streaming sequence verified! Side-channel is functioning correctly.")

if __name__ == "__main__":
    unittest.main()
