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

Progressive Disclosure (Anthropic 2.1H pattern):
- Tier 1 — ``catalog()``: name, summary, tags. Cheap to ship to LLMs.
- Tier 2 — ``inspect(name)``: full SKILL.md body + tool signatures.
- Tier 3 — ``get_tool(name)``: callable tool, invoked on demand.
"""

from pathlib import Path
from typing import Any, List

from loguru import logger


def _parse_skill_md(skill_md: Path) -> dict[str, Any]:
    """Extract YAML frontmatter + body from a SKILL.md file."""
    meta: dict[str, Any] = {}
    body = ""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return {"meta": meta, "body": body}

    if text.startswith("---"):
        try:
            import yaml

            parts = text.split("---", 2)
            if len(parts) >= 3:
                meta = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
        except Exception:  # noqa: BLE001
            body = text
    else:
        body = text

    if not isinstance(meta, dict):  # frontmatter wasn't a mapping
        meta = {"raw_frontmatter": meta}
    return {"meta": meta, "body": body}


def _summarise(body: str, max_chars: int = 240) -> str:
    """Pick a one-line summary from the SKILL body."""
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        return line[:max_chars]
    return ""


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
        *,
        summary: str = "",
        tags: list[str] | None = None,
        details: str = "",
        path: str | None = None,
    ):
        self.name = name
        self.description = description
        self.summary = summary or description[:240]
        self.version = version
        self.tools = tools or []
        self.prompts = prompts or {}
        self.config = config or {}
        self.tags = tags or []
        self.details = details
        self.path = path
        self.enabled = True

    # --- Tier 1: cheap catalog row -------------------------------------
    def to_catalog_entry(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "version": self.version,
            "tags": self.tags,
            "tool_count": len(self.tools),
            "enabled": self.enabled,
        }

    # --- Tier 2: full inspection --------------------------------------
    def to_detail(self) -> dict[str, Any]:
        return {
            **self.to_catalog_entry(),
            "description": self.description,
            "details": self.details,
            "path": self.path,
            "tools": [
                {
                    "name": getattr(t, "name", getattr(t, "__name__", "tool")),
                    "description": getattr(t, "description", "") or (
                        getattr(t, "__doc__", "") or ""
                    ).strip().splitlines()[0:1] and (
                        getattr(t, "__doc__", "") or ""
                    ).strip().splitlines()[0],
                }
                for t in self.tools
            ],
        }


class SkillRegistry:
    """
    Central registry for all available skills.

    Responsibilities:
    - Load skills from the skills directory
    - Register/unregister skills dynamically
    - Discover relevant skills based on task description
    - Provide tools and prompts to agents
    - Serve a 3-tier progressive disclosure surface (catalog / detail /
      callable tool)
    """

    def __init__(self, skills_dir: str = "skills") -> None:
        self._skills: dict[str, Skill] = {}
        self._skills_dir = Path(skills_dir)
        logger.info(f"🧩 SkillRegistry initialized (dir: {skills_dir})")

    async def load_all(self) -> None:
        """Scan Skills directory and load all valid skills.

        Parses SKILL.md frontmatter to populate Tier 1/2 metadata so the
        progressive-disclosure API can answer without re-reading files.
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

            parsed = _parse_skill_md(skill_md)
            meta = parsed["meta"]
            body = parsed["body"]

            tools: list[Any] = []
            try:
                module_name = f"app.skills.{skill_path.name}.tools"
                module = importlib.import_module(module_name)
                if hasattr(module, "get_tools") and callable(module.get_tools):
                    tools = module.get_tools()
                elif hasattr(module, "TOOLS") and isinstance(module.TOOLS, list):
                    tools = module.TOOLS
            except ImportError as e:
                logger.debug(
                    f"Skill '{skill_path.name}' has no loadable tools.py: {e}"
                )
            except Exception as e:  # noqa: BLE001
                logger.error(f"❌ Error loading tools for '{skill_path.name}': {e}")

            description = str(meta.get("description") or _summarise(body))
            self.register(
                Skill(
                    name=str(meta.get("name") or skill_path.name),
                    description=description,
                    summary=_summarise(body) or description,
                    version=str(meta.get("version") or "0.1.0"),
                    tools=tools,
                    tags=list(meta.get("tags") or []),
                    details=body,
                    path=str(skill_path),
                )
            )

    def register(self, skill: Skill) -> None:
        """Register a skill."""
        self._skills[skill.name] = skill
        logger.info(f"Skill registered: {skill.name} v{skill.version}")

    def unregister(self, name: str) -> None:
        """Unregister a skill."""
        if name in self._skills:
            del self._skills[name]

    # ------------------------------------------------------------------
    # Progressive Disclosure surface
    # ------------------------------------------------------------------
    def catalog(self, query: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Return Tier 1 catalog rows, optionally filtered by keyword."""
        rows = [s.to_catalog_entry() for s in self._skills.values() if s.enabled]
        if query:
            q = query.lower()
            rows = [
                r
                for r in rows
                if q in r["name"].lower()
                or q in (r["summary"] or "").lower()
                or any(q in t.lower() for t in r.get("tags", []))
            ]
        return rows[:limit]

    def inspect(self, name: str) -> dict[str, Any] | None:
        """Return Tier 2 detail for a single skill, or None."""
        skill = self._skills.get(name)
        return skill.to_detail() if skill and skill.enabled else None

    def discover(self, query: str, limit: int = 5) -> list[Skill]:
        """Discover skills relevant to a given task description.

        Lightweight keyword overlap scoring — sufficient for the agent's
        Tier 1 disclosure step. For semantic recall, prefer
        ``catalog(query)`` paired with the LLM's own re-ranking.
        """
        if not query:
            return [s for s in self._skills.values() if s.enabled][:limit]

        q_tokens = {t for t in query.lower().split() if len(t) > 2}
        scored: list[tuple[int, Skill]] = []
        for skill in self._skills.values():
            if not skill.enabled:
                continue
            haystack = " ".join(
                [skill.name, skill.summary, skill.description, *skill.tags]
            ).lower()
            score = sum(1 for tok in q_tokens if tok in haystack)
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

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


# ----- module-level singleton accessor ------------------------------------
_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
