"""Unit tests for ``scripts._export.packager.Packager``.

These tests build a tiny fake repo on disk and run the packager against it,
so they don't depend on the real ``backend/`` tree (and stay fast).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts._export.assets import scan_assets
from scripts._export.packager import (
    Packager,
    PackagerProgress,
    _backend_filter,
)
from scripts._export.schema import Blueprint


def _make_fake_repo(root: Path) -> None:
    """Create a minimal repo layout the packager can chew on."""
    # backend/
    (root / "backend" / "app").mkdir(parents=True)
    (root / "backend" / "app" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "backend" / "app" / "__init__.py").write_text("", encoding="utf-8")
    # excluded by filter
    (root / "backend" / "tests").mkdir()
    (root / "backend" / "tests" / "test_x.py").write_text("# excluded\n", encoding="utf-8")
    (root / "backend" / "test_root.py").write_text("# excluded\n", encoding="utf-8")
    (root / "backend" / "debug_foo.py").write_text("# excluded\n", encoding="utf-8")
    (root / "backend" / "data").mkdir()
    (root / "backend" / "data" / "blob.bin").write_text("x", encoding="utf-8")
    (root / "backend" / "app" / "__pycache__").mkdir()
    (root / "backend" / "app" / "__pycache__" / "main.cpython-311.pyc").write_text(
        "x", encoding="utf-8"
    )

    # frontend/dist
    (root / "frontend" / "dist").mkdir(parents=True)
    (root / "frontend" / "dist" / "index.html").write_text("<html/>", encoding="utf-8")

    # skills
    (root / "skills" / "alpha").mkdir(parents=True)
    (root / "skills" / "alpha" / "SKILL.md").write_text(
        "# Alpha\n\nDoes alpha things.\n", encoding="utf-8"
    )
    (root / "skills" / "beta").mkdir()
    (root / "skills" / "beta" / "SKILL.md").write_text(
        "# Beta\n\nDoes beta things.\n", encoding="utf-8"
    )

    # mcp-servers
    (root / "mcp-servers" / "erp").mkdir(parents=True)
    (root / "mcp-servers" / "erp" / "README.md").write_text(
        "ERP bridge.\n", encoding="utf-8"
    )

    # extras
    (root / "prompts").mkdir()
    (root / "prompts" / "quote_system.md").write_text("be helpful\n", encoding="utf-8")


def _bp(**overrides) -> Blueprint:
    base = {
        "name": "quote-bot",
        "version": "1.0.0",
        "customer": "ACME",
        "description": "test pkg",
        "platform_mode": "agent",
        "ui_mode": "single_agent",
        "llm": {"provider": "openai", "model": "gpt-4o-mini"},
        "agents": [
            {
                "id": "qb",
                "name": "Quote Bot",
                "skills": ["alpha"],
                "mcp_servers": ["erp"],
            }
        ],
        "extra_paths": ["prompts/quote_system.md"],
    }
    base.update(overrides)
    return Blueprint.model_validate(base)


# ── _backend_filter ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "rel,kept",
    [
        ("app/main.py", True),
        ("app/__init__.py", True),
        ("tests/test_x.py", False),
        ("test_root.py", False),
        ("debug_foo.py", False),
        ("data/blob.bin", False),
        ("app/__pycache__/main.cpython-311.pyc", False),
        ("logs/today.log", False),
        ("module.pyc", False),
    ],
)
def test_backend_filter(rel: str, kept: bool):
    assert _backend_filter(Path(rel)) is kept


# ── Asset scanning over the fake repo ──────────────────────────────────────


def test_scan_assets_on_fake_repo(tmp_path: Path):
    _make_fake_repo(tmp_path)
    catalog = scan_assets(tmp_path)
    assert {a.id for a in catalog.skills} == {"alpha", "beta"}
    assert {a.id for a in catalog.mcp_servers} == {"erp"}
    # description picked up from README/SKILL.md
    alpha = next(a for a in catalog.skills if a.id == "alpha")
    assert "alpha things" in alpha.description


# ── Full packager run on fake repo ─────────────────────────────────────────


def test_packager_full_run(tmp_path: Path):
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    _make_fake_repo(repo)

    events: list[PackagerProgress] = []
    pkg = Packager(_bp(), out, repo_root=repo)
    pkg.on_progress = events.append
    result = pkg.run(make_zip=True)

    # Pipeline reached every step
    steps_done = {ev.step for ev in events if ev.status == "ok"}
    assert {
        "validate",
        "layout",
        "copy_backend",
        "copy_frontend",
        "copy_assets",
        "write_env",
        "write_compose",
        "write_lock",
        "write_readme",
        "zip",
        "done",
    } <= steps_done

    # Generated artefacts present
    assert (out / "backend" / "app" / "main.py").exists()
    assert (out / "frontend_dist" / "index.html").exists()
    assert (out / "skills" / "alpha" / "SKILL.md").exists()
    assert (out / "mcp-servers" / "erp" / "README.md").exists()
    assert (out / "prompts" / "quote_system.md").exists()
    assert (out / ".env.example").exists()
    assert (out / "docker-compose.yml").exists()
    assert (out / "blueprint.lock.yaml").exists()
    assert (out / "blueprint.lock.json").exists()
    assert (out / "README_DEPLOY.md").exists()

    # Excluded files stay excluded
    assert not (out / "backend" / "tests").exists()
    assert not (out / "backend" / "data").exists()
    assert not (out / "backend" / "test_root.py").exists()
    assert not (out / "backend" / "debug_foo.py").exists()
    assert not (out / "backend" / "app" / "__pycache__").exists()

    # Unwanted skill (beta) not copied — only blueprint-referenced ones
    assert not (out / "skills" / "beta").exists()

    # Lock file round-trips
    lock = json.loads((out / "blueprint.lock.json").read_text(encoding="utf-8"))
    assert lock["name"] == "quote-bot"
    assert lock["agents"][0]["id"] == "qb"

    # ZIP exists and is non-trivial
    assert result.zip_path is not None
    assert result.zip_path.stat().st_size > 0
    assert result.files_written > 5
    assert result.bytes_written > 0


# ── Cross-validation warnings ──────────────────────────────────────────────


def test_packager_warns_on_unknown_skill(tmp_path: Path):
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    _make_fake_repo(repo)

    bp = _bp(
        agents=[{"id": "qb", "name": "Quote Bot", "skills": ["alpha", "ghost"]}],
        extra_paths=[],
    )
    events: list[PackagerProgress] = []
    pkg = Packager(bp, out, repo_root=repo)
    pkg.on_progress = events.append
    result = pkg.run(make_zip=False)

    assert any("ghost" in w for w in result.warnings)
    # Validate step emits a warn event for the unknown skill
    assert any(
        ev.step == "validate" and ev.status == "warn" and "ghost" in ev.detail
        for ev in events
    )


# ── overwrite=False refuses non-empty target ───────────────────────────────


def test_packager_refuses_non_empty_dir(tmp_path: Path):
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    _make_fake_repo(repo)
    out.mkdir()
    (out / "stale.txt").write_text("x", encoding="utf-8")

    pkg = Packager(_bp(), out, repo_root=repo, overwrite=False)
    with pytest.raises(FileExistsError):
        pkg.run(make_zip=False)


def test_packager_overwrite_clears_dir(tmp_path: Path):
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    _make_fake_repo(repo)
    out.mkdir()
    (out / "stale.txt").write_text("x", encoding="utf-8")

    pkg = Packager(_bp(), out, repo_root=repo, overwrite=True)
    pkg.run(make_zip=False)
    assert not (out / "stale.txt").exists()
    assert (out / ".env.example").exists()


# ── Generated env / compose / lock content sanity ──────────────────────────


def test_generated_env_contains_blueprint_values(tmp_path: Path):
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    _make_fake_repo(repo)
    Packager(
        _bp(llm={"provider": "openai", "model": "gpt-4o-mini", "base_url": "http://x/v1"}),
        out,
        repo_root=repo,
    ).run(make_zip=False)
    env_text = (out / ".env.example").read_text(encoding="utf-8")
    assert "PLATFORM_MODE=agent" in env_text
    assert "LLM_MODEL=gpt-4o-mini" in env_text
    assert "OPENAI_BASE_URL=http://x/v1" in env_text


def test_generated_compose_contains_image_name(tmp_path: Path):
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    _make_fake_repo(repo)
    Packager(_bp(), out, repo_root=repo).run(make_zip=False)
    compose = (out / "docker-compose.yml").read_text(encoding="utf-8")
    assert "quote-bot-backend:1.0.0" in compose
    assert 'PLATFORM_MODE: "agent"' in compose


def test_lock_yaml_round_trips(tmp_path: Path):
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    _make_fake_repo(repo)
    Packager(_bp(), out, repo_root=repo).run(make_zip=False)
    lock = yaml.safe_load((out / "blueprint.lock.yaml").read_text(encoding="utf-8"))
    Blueprint.model_validate(lock)  # must re-validate cleanly
