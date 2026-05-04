"""
Template Search Node.
Discovers existing skills and agent templates to prevent redundant development.
"""
import os
from typing import Any, List
import yaml
from langchain_core.messages import AIMessage
from app.core.llm_factory import get_chat_model
from pydantic import BaseModel, Field

from ..state import BuilderState
from app.skills.registry import get_skill_registry

class SearchQuery(BaseModel):
    query: str = Field(description="Search query to find relevant skills and agents.")
    reasoning: str = Field(description="Why this query was chosen.")

SEARCH_PROMPT = """You are the Discovery Agent for the Agent Builder Assistant.
Based on the current conversation and confirmed requirements, generate a single concise search query to find relevant existing skills or agent templates in our registry.

CURRENT REQUIREMENTS:
{confirmed_fields}

LATEST USER MESSAGE:
{latest_message}
"""

async def template_search_node(state: BuilderState) -> dict[str, Any]:
    """Search for existing templates, skills, or agents to anchor the discussion."""
    messages = state.get("messages", [])
    latest_message = messages[-1].content if messages else ""
    confirmed_fields = state.get("confirmed_fields", {})
    
    # 1. Use LLM to generate a search query
    llm = get_chat_model(temperature=0)
    query_generator = llm.with_structured_output(SearchQuery, method="function_calling")
    
    search_result: SearchQuery = await query_generator.ainvoke([
        {"role": "system", "content": SEARCH_PROMPT.format(
            confirmed_fields=str(confirmed_fields),
            latest_message=latest_message
        )}
    ])
    
    # 2. Search Skills
    registry = get_skill_registry()
    await registry.load_all()
    matched_skills = registry.discover(search_result.query, limit=5)
    
    # 3. Search Agent Templates (YAML files)
    matched_agents = []
    agent_dir = "backend/app/prompts/agents"
    if os.path.exists(agent_dir):
        for filename in os.listdir(agent_dir):
            if filename.endswith(".yaml"):
                # Very simple keyword check on filename or content
                if search_result.query.lower() in filename.lower():
                    matched_agents.append(filename.replace(".yaml", ""))
    
    # 4. Prepare Context
    discovered_context = state.get("discovered_context", {})
    discovered_context["matched_skills"] = [s.name for s in matched_skills]
    discovered_context["matched_agents"] = matched_agents
    
    # 5. Inform the user (if any matches found)
    response_msg = None
    if matched_skills or matched_agents:
        skill_str = ", ".join([s.name for s in matched_skills])
        agent_str = ", ".join(matched_agents)
        
        content = "🔍 [Discovery] I found some existing assets that might be useful:\n"
        if matched_skills:
            content += f"- **Existing Skills**: {skill_str}\n"
        if matched_agents:
            content += f"- **Agent Templates**: {agent_str}\n"
        content += "\nWe can leverage these to speed up development. Should we proceed with the interview or explore these?"
        
        response_msg = AIMessage(content=content)

    return {
        "discovered_context": discovered_context,
        "messages": [response_msg] if response_msg else [],
        "next_step": "interview"
    }
