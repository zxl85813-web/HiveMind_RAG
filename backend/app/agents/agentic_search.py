"""
Agentic Search Skills (Tier 0 Memory)
Anthropic-inspired JIT context acquisition tools.
"""

import fnmatch
import os

from langchain_core.tools import tool


@tool
async def list_files_recursive(directory: str = ".", pattern: str = "*", max_depth: int = 3) -> str:
    """
    List files in a directory recursively.
    Use this to explore the project structure or find specific files.
    pattern: glob pattern (e.g. "*.py", "README.md")
    """
    try:
        results = []
        # Security: prevent escaping workspace
        abs_base = os.path.abspath(directory)
        if not abs_base.startswith(os.getcwd()):
            return f"Error: Cannot access directory outside of workspace: {directory}"

        for root, dirs, files in os.walk(abs_base):
            depth = root[len(abs_base) :].count(os.sep)
            if depth >= max_depth:
                del dirs[:]  # Don't go deeper
                continue

            for filename in fnmatch.filter(files, pattern):
                rel_path = os.path.relpath(os.path.join(root, filename), os.getcwd())
                results.append(rel_path)

        if not results:
            return f"No files found matching '{pattern}' in {directory}"

        return "\n".join(results[:100])  # Limit output
    except Exception as e:
        return f"Error listing files: {e!s}"


@tool
async def grep_search(query: str, file_pattern: str = "*", case_sensitive: bool = False) -> str:
    """
    Search for a literal string across files (Grep-like).
    Use this for precise text search without indexing.
    """
    try:
        results = []
        count = 0
        for root, _, files in os.walk(os.getcwd()):
            # Skip hidden and big dirs
            if "/." in root or "node_modules" in root or "venv" in root:
                continue

            for filename in fnmatch.filter(files, file_pattern):
                path = os.path.join(root, filename)
                try:
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if (query in line) if case_sensitive else (query.lower() in line.lower()):
                                rel_path = os.path.relpath(path, os.getcwd())
                                results.append(f"{rel_path}:{line_no}: {line.strip()}")
                                count += 1
                                if count > 50:
                                    break
                except Exception:
                    continue
                if count > 50:
                    break
            if count > 50:
                break

        if not results:
            return f"No matches found for '{query}'"

        return "\n".join(results)
    except Exception as e:
        return f"Error in grep_search: {e!s}"


@tool
async def read_file_range(path: str, start_line: int = 1, end_line: int = 100) -> str:
    """
    Read specific lines from a file.
    Use this to inspect large files without loading them completely.
    """
    try:
        if not os.path.exists(path):
            return f"Error: File not found: {path}"

        lines = []
        with open(path, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if i >= start_line and i <= end_line:
                    lines.append(f"{i}: {line.rstrip()}")
                if i > end_line:
                    break

        return "\n".join(lines)
    except Exception as e:
        return f"Error reading file: {e!s}"


# Export search tools
SEARCH_TOOLS = [list_files_recursive, grep_search, read_file_range]


# ============================================================
#  Progressive Skill Disclosure Tools (2.1H)
#  Agents should call list_available_skills() FIRST, then
#  read_skill_detail(name) only for skills they actually need.
# ============================================================

@tool
def list_available_skills() -> str:
    """
    List all available skill packages with a one-line description each.
    ALWAYS call this first before reading any skill in detail.
    Then use read_skill_detail(name) to load only the skill(s) you need.
    """
    try:
        from app.skills.registry import SkillRegistry

        registry = SkillRegistry(skills_dir="app/skills")
        meta = registry.list_skill_metadata()
        if not meta:
            return "No skills registered. Skills directory may be empty or not yet loaded."
        lines = [f"[{i}] {m['name']} (v{m['version']}) — {m['description']}" for i, m in enumerate(meta)]
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing skills: {e}"


@tool
def read_skill_detail(skill_name: str) -> str:
    """
    Read the full SKILL.md documentation for a specific skill.
    Only call this after identifying the skill you need via list_available_skills().
    """
    try:
        from app.skills.registry import SkillRegistry

        registry = SkillRegistry(skills_dir="app/skills")
        # Load registry to populate skills
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(registry.load_all())
        loop.close()

        content = registry.read_skill_content(skill_name)
        if content is None:
            return f"Skill '{skill_name}' not found. Use list_available_skills() to see all available skills."
        return content
    except Exception as e:
        return f"Error reading skill '{skill_name}': {e}"


# Include new disclosure tools in export
SEARCH_TOOLS = [list_files_recursive, grep_search, read_file_range, list_available_skills, read_skill_detail]
