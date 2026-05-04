"""
Confirmation Node.
Presents the final architectural summary to the user for approval.
"""
from typing import Any
from langchain_core.messages import AIMessage
from ..state import BuilderState

async def confirm_node(state: BuilderState) -> dict[str, Any]:
    """Show the draft summary and ask for final confirmation."""
    confirmed_fields = state.get("confirmed_fields", {})
    
    summary = "📋 **Agent Final Specification Review**\n\n"
    for key, value in confirmed_fields.items():
        summary += f"- **{key.replace('_', ' ').title()}**: {value}\n"
    
    summary += "\n**Does this look correct?** If you approve, I will generate the final configuration and prepare the test harness."
    
    return {
        "messages": [AIMessage(content=summary)],
        "next_step": "pending_approval" # This would be handled by a router or human-in-the-loop
    }
