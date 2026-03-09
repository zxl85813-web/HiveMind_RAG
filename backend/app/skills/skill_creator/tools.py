"""
Tools for Skill Creator Meta-Skill.
"""

from pathlib import Path

from langchain_core.tools import tool


@tool
async def list_available_skills() -> list[str]:
    """List all skills currently maintained on the filesystem."""
    skills_dir = Path("app/skills")
    if not skills_dir.exists():
        return []

    skills = []
    for d in skills_dir.iterdir():
        if d.is_dir() and not d.name.startswith("__") and (d / "SKILL.md").exists():
            skills.append(d.name)

    return skills


TOOLS = [list_available_skills]
