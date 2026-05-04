"""
Smoke tests for SkillRegistry lifecycle helpers added in M7.

Covers:
- install_from_zip (happy path, missing SKILL.md, multi-root, path traversal,
  overwrite flag)
- toggle / uninstall / reload_async
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from app.skills.registry import SkillRegistry


SKILL_MD = """---
name: hello_skill
version: 0.1.0
summary: A hello-world skill
tags: [demo]
---

# Hello Skill

This skill says hello. Body content for the skill.
"""


def _make_zip(files: dict[str, str]) -> bytes:
    """Build an in-memory zip from {arcname: text}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.fixture()
def registry(tmp_path: Path) -> SkillRegistry:
    """Fresh registry rooted at a temp dir so tests cannot touch real skills."""
    return SkillRegistry(skills_dir=str(tmp_path / "skills"))


# ---------------------------------------------------------------------------
# install_from_zip
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_from_zip_happy_path(registry: SkillRegistry):
    payload = _make_zip({"hello_skill/SKILL.md": SKILL_MD})

    result = await registry.install_from_zip(payload)

    assert result["installed"] is True
    assert result["directory"] == "hello_skill"
    # Skill folder is on disk
    target = Path(registry._skills_dir) / "hello_skill" / "SKILL.md"
    assert target.exists()
    # And appears in the catalog
    names = [s["name"] for s in registry.catalog()]
    assert "hello_skill" in names


@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_rejects_missing_skill_md(registry: SkillRegistry):
    payload = _make_zip({"hello_skill/README.md": "no skill md here"})

    with pytest.raises(ValueError, match="SKILL.md"):
        await registry.install_from_zip(payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_rejects_multiple_top_level_folders(registry: SkillRegistry):
    payload = _make_zip({
        "a/SKILL.md": SKILL_MD,
        "b/SKILL.md": SKILL_MD,
    })

    with pytest.raises(ValueError, match="exactly one top-level"):
        await registry.install_from_zip(payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_rejects_path_traversal(registry: SkillRegistry):
    # Member trying to escape via ../
    payload = _make_zip({
        "hello_skill/SKILL.md": SKILL_MD,
        "hello_skill/../evil.txt": "pwned",
    })

    with pytest.raises(ValueError):
        await registry.install_from_zip(payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_overwrite_flag(registry: SkillRegistry):
    payload = _make_zip({"hello_skill/SKILL.md": SKILL_MD})
    await registry.install_from_zip(payload)

    # Re-install without overwrite should fail
    with pytest.raises(ValueError, match="already exists"):
        await registry.install_from_zip(payload)

    # With overwrite=True it should succeed
    result = await registry.install_from_zip(payload, overwrite=True)
    assert result["installed"] is True


# ---------------------------------------------------------------------------
# toggle / uninstall / reload
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_toggle_and_catalog_includes_disabled(registry: SkillRegistry):
    await registry.install_from_zip(_make_zip({"hello_skill/SKILL.md": SKILL_MD}))

    assert registry.toggle("hello_skill", False) is True
    rows = registry.catalog()
    found = next((r for r in rows if r["name"] == "hello_skill"), None)
    assert found is not None, "disabled skills must remain visible in catalog"
    assert found["enabled"] is False

    assert registry.toggle("does_not_exist", True) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_uninstall_removes_directory(registry: SkillRegistry):
    await registry.install_from_zip(_make_zip({"hello_skill/SKILL.md": SKILL_MD}))
    target = Path(registry._skills_dir) / "hello_skill"
    assert target.exists()

    assert registry.uninstall("hello_skill", delete_files=True) is True
    assert not target.exists()
    assert "hello_skill" not in [s["name"] for s in registry.catalog()]

    # Idempotent: second call returns False, does not raise
    assert registry.uninstall("hello_skill") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reload_async_rescans_dir(registry: SkillRegistry):
    # Manually drop a skill folder on disk, bypassing install_from_zip
    skill_dir = Path(registry._skills_dir) / "hello_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

    # Empty before reload
    assert registry.list_skills() == []

    count = await registry.reload_async()
    assert count == 1
    assert "hello_skill" in [s["name"] for s in registry.catalog()]
