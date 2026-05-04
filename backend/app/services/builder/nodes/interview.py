"""
Interview & Gap Analysis Node.
Conducts structured requirements elicitation and updates coverage metrics.
"""
from typing import Any, List, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm_factory import get_chat_model
from pydantic import BaseModel, Field

from ..state import BuilderState

# Define the core dimensions we need to build a high-quality Agent
CORE_DIMENSIONS = [
    "core_role",       # What is the agent's identity?
    "target_user",     # Who will use it?
    "boundary",        # What will it NOT do?
    "tools",           # What tools/skills are needed?
    "kb_bindings",     # Which Knowledge Bases should be linked?
    "tone_and_style",  # How should it talk?
    "guardrails",      # Critical safety/business rules
    "success_criteria" # How do we know it worked?
]

class RequirementExtraction(BaseModel):
    confirmed_fields: dict[str, Any] = Field(description="Dictionary of newly confirmed fields/dimensions.")
    missing_dimensions: List[str] = Field(description="List of dimensions still requiring clarification.")
    coverage_pct: float = Field(description="0.0 to 1.0, progress based on core dimensions.")
    assistant_response: str = Field(description="The next question or acknowledgement for the user.")

INTERVIEW_PROMPT = """You are the Lead Architect for the Agent Builder Assistant. 
Your goal is to extract a precise technical specification from the user to build an Agent.

### CORE DIMENSIONS TO COVER:
{all_dimensions}

### CURRENT PROGRESS:
- Confirmed Fields: {confirmed_fields}
- Current Coverage: {coverage_pct}%

### CONVERSATION HISTORY:
{history}

### YOUR TASKS:
1. **Analyze**: Identify which core dimensions are still missing or vague in the conversation history.
2. **Extract**: If the user just provided new information, update the `confirmed_fields`.
3. **Ask**: Choose the MOST IMPORTANT missing dimension and ask a targeted, professional question. 
4. **Style**: Be concise, architectural, and proactive. Do not just wait for the user to speak—guide them.

=== CRITICAL: NO VAGUE REQUIREMENTS ===
If a user says 'make it smart', push back and ask for specific behaviors or success criteria.
"""

async def interview_node(state: BuilderState) -> dict[str, Any]:
    """Extract requirements and conduct gap analysis."""
    messages = state.get("messages", [])
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages[-5:]])
    
    confirmed_fields = state.get("confirmed_fields", {})
    coverage_pct = state.get("coverage_pct", 0.0)

    llm = get_chat_model(temperature=0)
    extractor = llm.with_structured_output(RequirementExtraction, method="function_calling")
    
    prompt = ChatPromptTemplate.from_template(INTERVIEW_PROMPT)
    chain = prompt | extractor
    
    result: RequirementExtraction = await chain.ainvoke({
        "all_dimensions": ", ".join(CORE_DIMENSIONS),
        "confirmed_fields": str(confirmed_fields),
        "coverage_pct": int(coverage_pct * 100),
        "history": history_str
    })
    
    # Merge newly confirmed fields
    updated_fields = {**confirmed_fields, **result.confirmed_fields}
    
    # Recalculate coverage if not provided accurately by LLM
    confirmed_count = len([d for d in CORE_DIMENSIONS if d in updated_fields and updated_fields[d]])
    calculated_coverage = confirmed_count / len(CORE_DIMENSIONS)
    
    return {
        "confirmed_fields": updated_fields,
        "missing_dimensions": result.missing_dimensions,
        "coverage_pct": calculated_coverage,
        "messages": [AIMessage(content=result.assistant_response)],
        "interview_round": state.get("interview_round", 0) + 1
    }
