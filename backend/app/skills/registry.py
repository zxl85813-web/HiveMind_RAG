"""
模块级 docstring — Skills System — 模块化、可插拔的 Agent 能力包。

所属模块: skills
依赖模块: pathlib, importlib, loguru
注册位置: REGISTRY.md > Agent 模块 > SkillRegistry

A Skill is a self-contained package that provides:
- A description (SKILL.md) for agent discovery
- Tool functions that agents can invoke
- Prompt templates specific to the skill's domain
- Optional configuration

Skills are dynamically loaded and can be enabled/disabled at runtime.

2.1H Progressive Skill Disclosure:
  Agents should first call list_skill_metadata() to see a lightweight index,
  then read_skill_content(name) only for skills they actually need.
  This pattern prevents context explosion in large skill libraries.
"""

import re
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
        skill_md_path: Path | None = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.tools = tools or []
        self.prompts = prompts or {}
        self.config = config or {}
        self.enabled = True
        self._skill_md_path = skill_md_path  # lazy-read for Progressive Disclosure


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

    # ------------------------------------------------------------------
    # Progressive Skill Disclosure (2.1H)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter(content: str) -> dict[str, str]:
        """
        Parse YAML-style frontmatter delimited by '---' at the start of a file.
        Returns a dict of key→value strings. Safe (no PyYAML dependency).
        """
        content = content.lstrip()
        if not content.startswith("---"):
            return {}
        rest = content[3:]
        end = rest.find("\n---")
        if end == -1:
            return {}
        fm_block = rest[:end]
        meta: dict[str, str] = {}
        for line in fm_block.splitlines():
            m = re.match(r'^(\w[\w-]*):\s*"?(.*?)"?\s*$', line)
            if m:
                meta[m.group(1)] = m.group(2)
        return meta

    async def load_all(self) -> None:
        """
        Scan Skills directory and load all valid skills.

        2.1H Progressive Skill Disclosure:
        - Reads only SKILL.md frontmatter for the lightweight index.
        - Full SKILL.md content is only fetched on demand via read_skill_content().
        - tools.py is dynamically imported if present.
        """
        import importlib

        if not self._skills_dir.exists():
            logger.warning(f"Skills directory not found: {self._skills_dir}")
            return

        for skill_path in self._skills_dir.iterdir():
            if not skill_path.is_dir() or skill_path.name.startswith("__"):
                continue

            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                meta = self._parse_frontmatter(content)

                # Dynamic import of tools.py (optional)
                module_name = f"app.skills.{skill_path.name}.tools"
                tools: list[Any] = []
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, "get_tools") and callable(module.get_tools):
                        tools = module.get_tools()
                    elif hasattr(module, "TOOLS") and isinstance(module.TOOLS, list):
                        tools = module.TOOLS
                except ImportError:
                    pass  # Tools are optional; skill may only provide metadata

                skill = Skill(
                    name=meta.get("name", skill_path.name),
                    description=meta.get("description", f"Skill: {skill_path.name}"),
                    version=meta.get("version", "0.1.0"),
                    tools=tools,
                    skill_md_path=skill_md,
                )
                self.register(skill)

            except Exception as e:
                logger.error(f"❌ Error loading skill '{skill_path.name}': {e}")

    def list_skill_metadata(self) -> list[dict[str, str]]:
        """
        Return the lightweight metadata index (name, description, version).
        Agents should call this FIRST to discover available skills,
        then use read_skill_content() only for the ones they need.
        """
        return [
            {"name": s.name, "description": s.description, "version": s.version}
            for s in self._skills.values()
            if s.enabled
        ]

    def read_skill_content(self, name: str) -> str | None:
        """
        Read the full SKILL.md content for a specific skill.
        Returns None if the skill is not found or has no SKILL.md.
        """
        skill = self._skills.get(name)
        if skill is None:
            return None
        if skill._skill_md_path and skill._skill_md_path.exists():
            return skill._skill_md_path.read_text(encoding="utf-8", errors="ignore")
        return f"# {skill.name}\n{skill.description}"

    # ------------------------------------------------------------------
    # Core Registry Methods
    # ------------------------------------------------------------------

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
        Uses simple keyword matching against skill descriptions.
        """
        query_lower = query.lower()
        scored = []
        for s in self._skills.values():
            if not s.enabled:
                continue
            score = sum(1 for word in query_lower.split() if word in s.description.lower())
            scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]] if scored else list(self._skills.values())[:limit]

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

    def get_tool(self, tool_name: str) -> Any | None:
        """Get a specific tool function by name (e.g., 'parse_file')."""
        for skill in self._skills.values():
            if not skill.enabled:
                continue
            for tool in skill.tools:
                if hasattr(tool, "__name__") and tool.__name__ == tool_name:
                    return tool
                if hasattr(tool, "name") and tool.name == tool_name:
                    return tool
        return None

    def list_skills(self) -> list[Skill]:
        """List all registered skills."""
        return list(self._skills.values())


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
        import importlib

        if not self._skills_dir.exists():
            logger.warning(f"Skills directory not found: {self._skills_dir}")
            return

        for skill_path in self._skills_dir.iterdir():
            if not skill_path.is_dir() or skill_path.name.startswith("__"):
                continue

            # Check for SKILL.md marker file
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                # Dynamic import of tools.py
                # Assumes structure: app/skills/<name>/tools.py
                module_name = f"app.skills.{skill_path.name}.tools"
                try:
                    module = importlib.import_module(module_name)

                    # Look for tools export: TOOLS list or get_tools() function
                    tools = []
                    if hasattr(module, "get_tools") and callable(module.get_tools):
                        tools = module.get_tools()
                    elif hasattr(module, "TOOLS") and isinstance(module.TOOLS, list):
                        tools = module.TOOLS

                    # Create Skill object
                    # TODO: Parse SKILL.md frontmatter for description/version
                    skill = Skill(name=skill_path.name, description=f"Skill loaded from {skill_path.name}", tools=tools)
                    self.register(skill)

                except ImportError as e:
                    logger.warning(f"⚠️  Found skill '{skill_path.name}' but failed to load tools: {e}")

            except Exception as e:
                logger.error(f"❌ Error loading skill '{skill_path.name}': {e}")

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

    def get_tool(self, tool_name: str) -> Any | None:
        """Get a specific tool function by name (e.g., 'parse_file')."""
        for skill in self._skills.values():
            if not skill.enabled:
                continue
            for tool in skill.tools:
                # Check function name
                if hasattr(tool, "__name__") and tool.__name__ == tool_name:
                    return tool
                # Check for LangChain Tool 'name' attribute
                if hasattr(tool, "name") and tool.name == tool_name:
                    return tool
        return None

    def list_skills(self) -> list[Skill]:
        """List all registered skills."""
        return list(self._skills.values())
