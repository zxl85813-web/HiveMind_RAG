"""Asset discovery — scan the repo for available skills, MCP servers, agents.

Used by:
- The export packager (to validate blueprint references exist).
- The /api/export/assets endpoint (to populate the UI wizard pickers).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


# Repo root resolved from this file: <root>/scripts/_export/assets.py
REPO_ROOT = Path(__file__).resolve().parents[2]


class AssetEntry(BaseModel):
    id: str
    kind: Literal["skill", "mcp_server", "agent_template"]
    path: str  # repo-relative
    description: str = ""


class AssetCatalog(BaseModel):
    skills: list[AssetEntry] = []
    mcp_servers: list[AssetEntry] = []
    agent_templates: list[AssetEntry] = []


def _read_first_paragraph(md_path: Path, max_chars: int = 200) -> str:
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    # Strip leading H1 headings, keep the first non-empty paragraph.
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    for chunk in chunks:
        if chunk.startswith("#"):
            continue
        return chunk[:max_chars].replace("\n", " ").strip()
    return ""


def _scan_skills(root: Path) -> list[AssetEntry]:
    """Skills live as top-level dirs under ``skills/`` with a ``SKILL.md``."""
    skills_dir = root / "skills"
    out: list[AssetEntry] = []
    if not skills_dir.is_dir():
        return out
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        marker = child / "SKILL.md"
        if not marker.exists():
            continue
        out.append(
            AssetEntry(
                id=child.name,
                kind="skill",
                path=str(child.relative_to(root)).replace("\\", "/"),
                description=_read_first_paragraph(marker),
            )
        )
    return out


def _scan_mcp_servers(root: Path) -> list[AssetEntry]:
    mcp_dir = root / "mcp-servers"
    out: list[AssetEntry] = []
    if not mcp_dir.is_dir():
        return out
    for child in sorted(mcp_dir.iterdir()):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        readme = next(
            (child / n for n in ("README.md", "readme.md") if (child / n).exists()),
            None,
        )
        out.append(
            AssetEntry(
                id=child.name,
                kind="mcp_server",
                path=str(child.relative_to(root)).replace("\\", "/"),
                description=_read_first_paragraph(readme) if readme else "",
            )
        )
    return out


def _scan_agent_templates(root: Path) -> list[AssetEntry]:
    """Optional: pre-defined agent templates under ``blueprints/templates/``."""
    tpl_dir = root / "blueprints" / "templates"
    out: list[AssetEntry] = []
    if not tpl_dir.is_dir():
        return out
    for child in sorted(tpl_dir.glob("*.yaml")):
        out.append(
            AssetEntry(
                id=child.stem,
                kind="agent_template",
                path=str(child.relative_to(root)).replace("\\", "/"),
                description="",
            )
        )
    return out


def scan_assets(root: Path | None = None) -> AssetCatalog:
    """Scan the repo for installable assets a blueprint can reference."""
    base = root or REPO_ROOT
    return AssetCatalog(
        skills=_scan_skills(base),
        mcp_servers=_scan_mcp_servers(base),
        agent_templates=_scan_agent_templates(base),
    )
