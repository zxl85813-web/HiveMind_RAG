"""
Eval Preview Node.
Runs a background evaluation of the draft agent against the golden dataset.
"""
from typing import Any
from langchain_core.messages import AIMessage
from ..state import BuilderState
from ..harness_service import HarnessService

async def eval_preview_node(state: BuilderState) -> dict[str, Any]:
    """Runs a preliminary evaluation in the sandbox."""
    harness = HarnessService()
    
    # 1. Construct a temporary config for the draft
    draft_config = {
        "name": "Draft Agent Preview",
        "system_prompt": state.get("confirmed_fields", {}).get("core_role", "You are an assistant."),
        "tools": state.get("confirmed_fields", {}).get("tools", [])
    }
    
    # 2. Run Eval
    golden_dataset = state.get("golden_dataset", [])
    if not golden_dataset:
        return {"messages": [AIMessage(content="⚠️ No test cases found to evaluate.")]}

    # Signal to user we are starting eval
    # (In a real async graph, we might use multiple turns or a streamer)
    
    results = await harness.run_evaluation(draft_config, golden_dataset)
    
    # 3. Format results
    avg_score = sum(r.score for r in results) / len(results) if results else 0
    
    summary = f"🧪 **Sandbox Evaluation Results**\n\n"
    summary += f"- **Average Score**: {avg_score:.2f} / 1.0\n"
    summary += f"- **Test Cases**: {len(results)}\n\n"
    
    for i, res in enumerate(results):
        status = "✅" if res.score > 0.7 else "❌"
        summary += f"{status} **Case {i+1}**: {res.verdict} (Score: {res.score})\n"
        summary += f"   *Reasoning*: {res.reasoning[:100]}...\n"

    return {
        "messages": [AIMessage(content=summary)],
        "next_step": "confirm"
    }
