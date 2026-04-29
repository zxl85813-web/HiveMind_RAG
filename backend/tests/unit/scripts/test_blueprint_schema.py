"""Unit tests for ``scripts._export.schema.Blueprint``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from scripts._export.schema import (
    Blueprint,
    LLMProviderEnum,
    PlatformModeEnum,
    UIModeEnum,
    load_blueprint,
)


def _minimal_dict(**overrides):
    base = {
        "name": "quote-bot",
        "version": "1.0.0",
        "customer": "ACME",
        "platform_mode": "agent",
        "ui_mode": "single_agent",
        "llm": {"provider": "openai", "model": "gpt-4o-mini"},
        "agents": [{"id": "qb", "name": "Quote Bot"}],
    }
    base.update(overrides)
    return base


# ── Slug validation ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    ["a", "1bot", "Bot", "quote_bot", "quote bot", "-bot", "x" * 51, ""],
)
def test_name_rejects_bad_slugs(name):
    with pytest.raises(ValidationError):
        Blueprint.model_validate(_minimal_dict(name=name))


@pytest.mark.parametrize("name", ["ab", "quote-bot", "x123", "a-b-c-1"])
def test_name_accepts_good_slugs(name):
    bp = Blueprint.model_validate(_minimal_dict(name=name))
    assert bp.name == name


# ── default_agent_id cross-validation ──────────────────────────────────────


def test_default_agent_id_must_exist():
    with pytest.raises(ValidationError) as exc:
        Blueprint.model_validate(_minimal_dict(default_agent_id="nope"))
    assert "default_agent_id" in str(exc.value)


def test_default_agent_id_accepted_when_present():
    bp = Blueprint.model_validate(_minimal_dict(default_agent_id="qb"))
    assert bp.default_agent_id == "qb"


def test_resolved_default_agent_id_falls_back_to_first():
    bp = Blueprint.model_validate(_minimal_dict())
    assert bp.resolved_default_agent_id() == "qb"


def test_resolved_default_agent_id_none_when_no_agents():
    bp = Blueprint.model_validate(_minimal_dict(agents=[]))
    assert bp.resolved_default_agent_id() is None


# ── Enums coerce from strings ──────────────────────────────────────────────


def test_enums_coerced_from_strings():
    bp = Blueprint.model_validate(_minimal_dict())
    assert bp.platform_mode is PlatformModeEnum.AGENT
    assert bp.ui_mode is UIModeEnum.SINGLE_AGENT
    assert bp.llm.provider is LLMProviderEnum.OPENAI


# ── Loader round-trip ──────────────────────────────────────────────────────


def test_load_blueprint_yaml(tmp_path: Path):
    p = tmp_path / "bp.yaml"
    p.write_text(yaml.safe_dump(_minimal_dict()), encoding="utf-8")
    assert load_blueprint(p).name == "quote-bot"


def test_load_blueprint_json(tmp_path: Path):
    p = tmp_path / "bp.json"
    p.write_text(json.dumps(_minimal_dict()), encoding="utf-8")
    assert load_blueprint(p).name == "quote-bot"


def test_load_blueprint_rejects_non_mapping(tmp_path: Path):
    p = tmp_path / "bp.yaml"
    p.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a mapping"):
        load_blueprint(p)


# ── env_overrides allow extras ─────────────────────────────────────────────


def test_env_overrides_allow_extra_keys():
    d = _minimal_dict(env_overrides={"DISABLE_TELEMETRY": True, "CUSTOM_KNOB": "x"})
    bp = Blueprint.model_validate(d)
    dumped = bp.env_overrides.model_dump(exclude_none=True)
    assert dumped["CUSTOM_KNOB"] == "x"
