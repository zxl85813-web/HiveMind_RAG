"""
[RULE-B001]: Swarm Reflection Node.
Extracted from swarm.py.
"""

import json
from loguru import logger
from app.agents.schemas import SwarmState

async def reflection_node(orchestrator, state: SwarmState) -> dict:
    """
    Reflection node — evaluates agent output quality using LLM.
    """
    last_message = state["messages"][-1]
    reflection_count = state.get("reflection_count", 0) + 1

    logger.info(f"🪞 Reflection #{reflection_count}...")

    if reflection_count > 3:
        logger.warning("🪞 Too many reflections, forcing FINISH")
        return {"reflection_count": reflection_count, "next_step": "FINISH"}

    content = getattr(last_message, "content", "") or ""
    hard_violations: list[str] = []

    if len(content.strip()) < 5:
        hard_violations.append("empty_response")

    _PROHIBITED_PATTERNS = ["<script", "javascript:", "DROP TABLE", "sudo rm -rf"]
    for pattern in _PROHIBITED_PATTERNS:
        if pattern.lower() in content.lower():
            hard_violations.append(f"prohibited_content:{pattern[:24]}")
            break

    if hard_violations:
        return {
            "reflection_count": reflection_count,
            "next_step": "supervisor",
            "hard_rule_violations": hard_violations,
        }

    from app.services.evaluation.multi_grader import MultiGraderEval
    evaluator = MultiGraderEval()
    context_data = state.get("context_data", "")
    
    eval_result = await evaluator.evaluate(
        query=state.get("original_query", ""), 
        response=content, 
        context=context_data
    )

    prompt_variant = state.get("prompt_variant", "default")
    suggested_variant = prompt_variant
    
    next_step = "FINISH" if eval_result.verdict in ["PASS", "EXCELLENT"] else "supervisor"
    should_escalate = eval_result.verdict == "ESCALATE"

    return {
        "reflection_count": reflection_count,
        "next_step": next_step,
        "prompt_variant": suggested_variant,
        "force_reasoning_tier": should_escalate,
    }
