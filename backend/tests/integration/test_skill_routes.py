"""
Integration tests for the Skill management routes added in M7.

We bypass FastAPI's ASGI machinery and call the route functions directly,
swapping the module-level skill registry singleton for a temp-dir registry
so tests are hermetic.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException, UploadFile

from app.skills.registry import SkillRegistry


SKILL_MD = """---
name: route_skill
version: 1.2.3
summary: Smoke skill for route tests
---

# Route Skill
"""


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("route_skill/SKILL.md", SKILL_MD)
    return buf.getvalue()


@pytest.fixture()
def temp_registry(tmp_path: Path):
    """Patch ``get_skill_registry`` to return a temp-dir registry."""
    reg = SkillRegistry(skills_dir=str(tmp_path / "skills"))
    with patch("app.skills.registry.get_skill_registry", return_value=reg):
        yield reg


@pytest.mark.integration
@pytest.mark.asyncio
async def test_skill_routes_full_lifecycle(temp_registry: SkillRegistry):
    """upload → toggle → uninstall → reload, all via the route handlers."""
    from app.api.routes.agents import (
        install_skill_zip,
        toggle_skill,
        uninstall_skill,
        reload_skills,
        get_skills,
    )

    # 1) Upload via UploadFile
    upload = UploadFile(filename="route_skill.zip", file=io.BytesIO(_zip_bytes()))
    res = await install_skill_zip(file=upload, overwrite=False)
    assert res.success is True
    assert res.data["installed"] is True
    assert res.data["directory"] == "route_skill"

    # 2) Catalog lists it
    listing = await get_skills(query=None, limit=50)
    names = [r["name"] for r in listing.data]
    assert "route_skill" in names

    # 3) Toggle disable, then re-enable
    res = await toggle_skill("route_skill", enabled=False)
    assert res.data == {"name": "route_skill", "enabled": False}
    res = await toggle_skill("route_skill", enabled=True)
    assert res.data["enabled"] is True

    # 4) Reload counts the same skill
    res = await reload_skills()
    assert res.data["reloaded"] is True
    assert res.data["skill_count"] >= 1

    # 5) Uninstall removes it from disk
    skill_dir = Path(temp_registry._skills_dir) / "route_skill"
    assert skill_dir.exists()
    res = await uninstall_skill("route_skill", delete_files=True)
    assert res.data["deleted"] is True
    assert not skill_dir.exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_install_rejects_non_zip(temp_registry: SkillRegistry):
    from app.api.routes.agents import install_skill_zip

    upload = UploadFile(filename="payload.tar.gz", file=io.BytesIO(b"not a zip"))
    with pytest.raises(HTTPException) as exc:
        await install_skill_zip(file=upload, overwrite=False)
    assert exc.value.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_install_rejects_empty_upload(temp_registry: SkillRegistry):
    from app.api.routes.agents import install_skill_zip

    upload = UploadFile(filename="empty.zip", file=io.BytesIO(b""))
    with pytest.raises(HTTPException) as exc:
        await install_skill_zip(file=upload, overwrite=False)
    assert exc.value.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uninstall_404(temp_registry: SkillRegistry):
    from app.api.routes.agents import uninstall_skill

    with pytest.raises(HTTPException) as exc:
        await uninstall_skill("does_not_exist", delete_files=True)
    assert exc.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_toggle_404(temp_registry: SkillRegistry):
    from app.api.routes.agents import toggle_skill

    with pytest.raises(HTTPException) as exc:
        await toggle_skill("nope", enabled=True)
    assert exc.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_install_overwrite_via_route(temp_registry: SkillRegistry):
    from app.api.routes.agents import install_skill_zip

    payload = _zip_bytes()
    await install_skill_zip(
        file=UploadFile(filename="x.zip", file=io.BytesIO(payload)),
        overwrite=False,
    )

    # Without overwrite → 400
    with pytest.raises(HTTPException) as exc:
        await install_skill_zip(
            file=UploadFile(filename="x.zip", file=io.BytesIO(payload)),
            overwrite=False,
        )
    assert exc.value.status_code == 400

    # With overwrite → 200
    res = await install_skill_zip(
        file=UploadFile(filename="x.zip", file=io.BytesIO(payload)),
        overwrite=True,
    )
    assert res.success is True
