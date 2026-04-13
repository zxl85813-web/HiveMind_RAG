"""
[RULE-B001]: Swarm Utility Nodes.
Extracted from swarm.py.
"""

from loguru import logger
from langchain_core.messages import AIMessage
from app.agents.schemas import SwarmState

async def platform_action_node(orchestrator, state: SwarmState) -> dict:
    """Handles platform-specific actions like modal popups or navigation."""
    logger.info("[PlatformAction] Responding with direct action reply")
    # Content is usually passed via context_data by the supervisor
    reply = state.get("context_data", "Action executed.")
    return {
        "messages": [AIMessage(content=reply)],
        "agent_outputs": {"platform_action": reply},
    }

async def reflection_decision_node(orchestrator, state: SwarmState) -> dict:
    """Decision node to determine if explicit reflection is required."""
    uncertainty = state.get("uncertainty_level", 0.5)
    last_node = state.get("last_node_id", "")
    agent_outputs = state.get("agent_outputs", {})
    last_output = list(agent_outputs.values())[-1] if agent_outputs else ""

    # 1. Hard Rule: Security check (Cheap/Local)
    from app.services.security.sanitizer import SecuritySanitizer
    if SecuritySanitizer.contains_sensitive_data(str(last_output)):
        logger.warning("🛡️ [Reflection Decision] Sensitive data detected. Forcing Reflection.")
        return {"next_step": "REFLECTION"}

    # 2. Heuristic: Confidence & Node Type
    is_complex = any(agent in last_node for agent in ["code", "sql", "orchestrator"])
    if uncertainty < 0.3 and not is_complex:
        logger.info(f"⚡ [Reflection Decision] High confidence ({uncertainty:.2f}) & Low complexity. Skipping Reflection.")
        return {"next_step": "FINISH"}

    # 3. Default: Fallback to Reflection for safety
    logger.info(f"🪞 [Reflection Decision] Proceeding to Reflection (Uncertainty: {uncertainty:.2f}).")
    return {"next_step": "REFLECTION"}
