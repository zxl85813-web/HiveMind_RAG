"""
Scope Guardian Node.
Implements the Anti-Sycophancy and Scope Lock protocols.
"""
from typing import Any
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm_factory import get_chat_model
from pydantic import BaseModel, Field

from ..state import BuilderState
# Assuming we have a way to get the LLM. 
# We'll import get_llm or just use a placeholder for the actual model instantiation.
# For now, we will use standard langchain ChatOpenAI or similar based on project conventions.
# We'll use a dummy import or rely on the caller to provide it, but normally it's initialized here.

class ScopeCheckResult(BaseModel):
    is_creep: bool = Field(
        description="True if the user is adding features that inflate the scope beyond the core goal."
    )
    reason: str = Field(
        description="Reasoning for the decision."
    )
    suggested_pushback: str | None = Field(
        description="If is_creep is True, the exact polite pushback message the assistant should say."
    )

SCOPE_GUARDIAN_PROMPT = """You are the Scope Guardian for the Agent Builder Assistant. Your role is exclusively to prevent 'Scope Creep' and enforce 'Anti-Sycophancy' protocols.

=== CRITICAL: ANTI-SYCOPHANCY MODE ===
You are STRICTLY PROHIBITED from:
- Agreeing to features that expand the system's core boundaries
- Recommending complex tools when a simple one suffices
- Being overly accommodating ("Sycophantic") to the user's feature bloat requests

Your job is NOT to be a helpful assistant that agrees to everything. Your job is to be the strict architectural gatekeeper.

## Your Process

1. **Understand Boundaries**: Review the `CURRENT CORE REQUIREMENTS` below.
2. **Analyze Latest Request**: Look at the `LATEST CONVERSATION`. Is the user attempting to expand the scope unnecessarily?
3. **Determine Scope Creep**: 
   - Is it unrelated to the core goal?
   - Is it a "nice-to-have" that should wait for V2?
   - Is it adding complex infrastructure when the core is simple?
4. **Pushback Strategy**: If scope creep is detected, provide a polite but firm pushback, refusing the feature and suggesting keeping it simple for V1.

CURRENT CORE REQUIREMENTS:
{confirmed_fields}

LATEST CONVERSATION:
{recent_messages}

Return your structured judgment based on the above criteria.
"""

async def scope_guardian_node(state: BuilderState) -> dict[str, Any]:
    """Check for scope creep and enforce anti-sycophancy rules."""
    messages = state.get("messages", [])
    if not messages:
        return {"next_step": "ok"}
    
    # We only check if the last message is from the user
    last_msg = messages[-1]
    if last_msg.type != "human":
        return {"next_step": "ok"}

    # In a real setup, import the configured model
    # 1. Determine if latest input is Scope Creep
    llm = get_chat_model(temperature=0)
    
    # We use structured output
    evaluator = llm.with_structured_output(ScopeCheckResult, method="function_calling")
    
    prompt = ChatPromptTemplate.from_template(SCOPE_GUARDIAN_PROMPT)
    chain = prompt | evaluator
    
    # Prepare inputs
    recent_msgs_str = "\n".join([f"{m.type}: {m.content}" for m in messages[-3:]])
    confirmed_fields_str = str(state.get("confirmed_fields", "None yet"))
    
    result: ScopeCheckResult = await chain.ainvoke({
        "confirmed_fields": confirmed_fields_str,
        "recent_messages": recent_msgs_str
    })
    
    if result.is_creep:
        count = state.get("added_features_count", 0) + 1
        
        # We inject the pushback directly into the messages
        pushback_msg = AIMessage(content=f"⚠️ [Scope Guardian Alert] {result.suggested_pushback}")
        
        if count >= 3:
            # Hard stop
            pushback_msg.content += "\n\nWe have reached the maximum allowed scope expansions for this draft. We must finalize the core first."
            return {
                "added_features_count": count,
                "scope_warning": "Hard stop reached.",
                "messages": [pushback_msg],
                "next_step": "force_scope_review"
            }
        else:
            return {
                "added_features_count": count,
                "messages": [pushback_msg],
                "next_step": "warn_scope" # Sends back to interview
            }
            
    return {"next_step": "context_injection"}
