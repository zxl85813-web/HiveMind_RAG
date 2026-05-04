"""
Skill Discovery Tool.
Allows agents to search the SkillRegistry for relevant capabilities.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.skills.registry import get_skill_registry

class DiscoveryQuery(BaseModel):
    query: str = Field(description="Natural language description of the capability needed.")
    tags: Optional[List[str]] = Field(default=None, description="Optional tags to filter by (e.g., 'rag', 'sql').")

def search_skills(query: str, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Search for relevant skills in the registry.
    Use this to find tools that match a user's requirements.
    """
    registry = get_skill_registry()
    results = registry.discover(query, limit=5)
    
    # Filter by tags if provided
    if tags:
        results = [s for s in results if any(t in s.tags for t in tags)]
        
    return [
        {
            "name": s.name,
            "summary": s.summary,
            "tags": s.tags,
            "tools": [t.__name__ for t in s.tools] if hasattr(s.tools, '__iter__') else []
        } 
        for s in results
    ]

def inspect_skill(skill_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific skill, including its full documentation.
    """
    registry = get_skill_registry()
    skill = registry.get_skill(skill_name)
    if not skill:
        return {"error": f"Skill '{skill_name}' not found."}
        
    return {
        "name": skill.name,
        "description": skill.description,
        "details": skill.details,
        "tools_signatures": [str(t) for t in skill.tools] if hasattr(skill.tools, '__iter__') else []
    }
