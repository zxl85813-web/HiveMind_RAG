"""
Config Generation Node.
Synthesizes the interview results into a persistent AgentConfig model.
"""
import yaml
from typing import Any
from langchain_core.messages import AIMessage
from app.core.llm_factory import get_chat_model
from pydantic import BaseModel, Field

from ..state import BuilderState
from app.models.builder import AgentConfig, EvalHarness
from app.core.config import settings # Assuming standard settings for DB
# We'll use a placeholder for the actual DB session logic
# In a real app, this would be injected via dependency or context

class GeneratedAgentPayload(BaseModel):
    name: str = Field(description="Short, unique name for the agent.")
    role: str = Field(description="The primary role/persona.")
    system_prompt: str = Field(description="The full, detailed system prompt including constraints and instructions.")
    tools_required: list[str] = Field(description="List of tool/skill names identified during discovery.")
    initial_config: dict[str, Any] = Field(description="Additional configuration parameters.")

GENERATOR_PROMPT = """You are the Lead Developer for the Agent Builder Assistant.
Your task is to synthesize the following interview data into a final, production-ready Agent Configuration.

CORE REQUIREMENTS:
{confirmed_fields}

DISCOVERED CONTEXT (Skills/Agents):
{discovered_context}

CONVERSATION LOG:
{history}

### INSTRUCTIONS:
1. **Persona**: Create a robust, professional system prompt following the best practices (similar to Claude Code).
2. **Tools**: Ensure the `tools_required` matches the technical capabilities discussed.
3. **Massive Tool Strategy**: If more than 5 tools are required, instruct the agent to use a hierarchical discovery pattern.
4. **Self-Correction**: Explicitly add instructions for the agent to handle tool execution errors (e.g., 'If a tool returns a validation error, analyze the schema and fix the parameters before retrying').
5. **Draft**: The name should be URL-safe (e.g., 'customer-support-bot').

Return the structured configuration payload.
"""

async def generate_config_node(state: BuilderState) -> dict[str, Any]:
    """Generate the final AgentConfig and EvalHarness models."""
    messages = state.get("messages", [])
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages[-10:]])
    confirmed_fields = state.get("confirmed_fields", {})
    discovered_context = state.get("discovered_context", {})

    llm = get_chat_model(temperature=0.1) # Use a stronger model for final generation
    generator = llm.with_structured_output(GeneratedAgentPayload, method="function_calling")
    
    prompt = ChatPromptTemplate.from_template(GENERATOR_PROMPT)
    chain = prompt | generator
    
    payload: GeneratedAgentPayload = await chain.ainvoke({
        "confirmed_fields": str(confirmed_fields),
        "discovered_context": str(discovered_context),
        "history": history_str
    })
    
    # In a real implementation, we would save to DB here.
    # For now, we simulate the persistence.
    generated_config = {
        "name": payload.name,
        "role": payload.role,
        "system_prompt": payload.system_prompt,
        "tools": payload.tools_required,
        "config_yaml": yaml.dump(payload.initial_config),
        "status": "draft"
    }
    
    success_msg = AIMessage(content=f"""🎉 **Agent Configuration Generated!**

**Name**: {payload.name}
**Role**: {payload.role}
**Tools**: {', '.join(payload.tools_required)}

The agent has been saved as a draft. You can now proceed to the **Sandbox** to run evaluations against your Golden Dataset.
""")

    return {
        "generated_config": generated_config,
        "messages": [success_msg],
        "next_step": "completed"
    }
