"""
Skills System — modular, pluggable capability packages for agents.

A Skill is a self-contained package that provides:
- A description (SKILL.md) for agent discovery
- Tool functions that agents can invoke
- Prompt templates specific to the skill's domain
- Optional configuration

Skills are dynamically loaded and can be enabled/disabled at runtime.
"""

from pathlib import Path
from typing import Any

from loguru import logger


class Skill:
    """Represents a loaded skill package."""

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "0.1.0",
        tools: list[Any] | None = None,
        prompts: dict[str, str] | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.tools = tools or []
        self.prompts = prompts or {}
        self.config = config or {}
        self.enabled = True


class SkillRegistry:
    """
    Central registry for all available skills.

    Responsibilities:
    - Load skills from the skills directory
    - Register/unregister skills dynamically
    - Discover relevant skills based on task description
    - Provide tools and prompts to agents
    """

    def __init__(self, skills_dir: str = "skills") -> None:
        self._skills: dict[str, Skill] = {}
        self._skills_dir = Path(skills_dir)
        logger.info(f"🧩 SkillRegistry initialized (dir: {skills_dir})")

    async def load_all(self) -> None:
        """Scan Skills directory and load all valid skills."""
        # TODO: Implement
        # - Walk skills_dir
        # - Find SKILL.md in each subdirectory
        # - Parse frontmatter for metadata
        # - Import tools.py for tool functions
        # - Register skill
        pass

    def register(self, skill: Skill) -> None:
        """Register a skill."""
        self._skills[skill.name] = skill
        logger.info(f"Skill registered: {skill.name} v{skill.version}")

    def unregister(self, name: str) -> None:
        """Unregister a skill."""
        if name in self._skills:
            del self._skills[name]

    def discover(self, query: str, limit: int = 5) -> list[Skill]:
        """
        Discover skills relevant to a given task description.
        Uses semantic matching against skill descriptions.
        """
        # TODO: Implement semantic search over skill descriptions
        return [s for s in self._skills.values() if s.enabled][:limit]

    def get_skill(self, name: str) -> Skill | None:
        """Get a specific skill by name."""
        return self._skills.get(name)

    def get_all_tools(self) -> list[Any]:
        """Get all tools from all enabled skills."""
        tools = []
        for skill in self._skills.values():
            if skill.enabled:
                tools.extend(skill.tools)
        return tools

    def list_skills(self) -> list[Skill]:
        """List all registered skills."""
        return list(self._skills.values())
