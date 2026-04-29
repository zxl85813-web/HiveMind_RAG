"""Blueprint schema — declarative spec for one customer delivery package.

A *blueprint* describes WHAT to ship. The packager turns it into HOW
(file copy + env generation + compose template).

Designed to be:
- Forward-compatible: unknown fields under ``extra`` are preserved verbatim.
- UI-friendly: every field has a ``description`` so the wizard can render hints.
- CLI-friendly: ``load_blueprint(path)`` accepts YAML or JSON.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


# ── Enums (kept as plain str enums so YAML/JSON serialize cleanly) ──────────


class PlatformModeEnum(str, Enum):
    RAG = "rag"
    AGENT = "agent"
    FULL = "full"


class UIModeEnum(str, Enum):
    FULL = "full"                # Default — show all routes/menus permitted by platform_mode
    SINGLE_AGENT = "single_agent"  # Strip layout to a single ChatPage
    WIDGET = "widget"            # Build only an embeddable widget bundle


class LLMProviderEnum(str, Enum):
    OPENAI = "openai"
    ARK = "ark"
    LOCAL_VLLM = "local_vllm"
    OLLAMA = "ollama"
    OTHER = "other"


class VectorStoreEnum(str, Enum):
    CHROMA = "chroma"
    ELASTICSEARCH = "elasticsearch"
    MILVUS = "milvus"
    QDRANT = "qdrant"


# ── Sub-models ──────────────────────────────────────────────────────────────


class LLMSpec(BaseModel):
    provider: LLMProviderEnum = Field(
        LLMProviderEnum.OPENAI, description="LLM backend the agent will call."
    )
    model: str = Field(..., description="Model identifier passed to the provider.")
    base_url: str | None = Field(
        None, description="Override base URL (intranet vLLM, Ark proxy, etc.)."
    )


class AgentSpec(BaseModel):
    id: str = Field(..., description="Agent identifier — used as default in single_agent UI mode.")
    name: str = Field(..., description="Human-readable name shown in UI.")
    system_prompt: str | None = Field(
        None,
        description="Inline system prompt OR a path (relative to repo root) to a .md file.",
    )
    skills: list[str] = Field(
        default_factory=list, description="Skill names (must exist under skills/)."
    )
    mcp_servers: list[str] = Field(
        default_factory=list, description="MCP server folder names (must exist under mcp-servers/)."
    )


class EnvOverrides(BaseModel):
    """Key/value pairs written verbatim into the generated .env.example."""

    model_config = {"extra": "allow"}

    # Common knobs surfaced for IDE/UI hints; everything else is allowed via extra.
    PLATFORM_MODE: str | None = None
    EMBEDDING_PROVIDER: str | None = None
    VECTOR_STORE_TYPE: VectorStoreEnum | None = None
    CHROMA_PERSIST_DIR: str | None = None
    ELASTICSEARCH_URL: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_API_KEY: str | None = None
    ARK_API_KEY: str | None = None
    DISABLE_TELEMETRY: bool | None = True


# ── Root model ──────────────────────────────────────────────────────────────


_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,49}$")


class Blueprint(BaseModel):
    """Top-level blueprint document."""

    # Metadata
    name: str = Field(..., description="Slug-style identifier (lowercase, hyphens).")
    version: str = Field("1.0.0", description="Semver-style version of this delivery.")
    customer: str = Field(..., description="Customer / tenant the package targets.")
    description: str = Field("", description="Free-form description shown in README.")

    # Behaviour
    platform_mode: PlatformModeEnum = Field(
        PlatformModeEnum.AGENT,
        description="Which backend modules to include (rag/agent/full).",
    )
    ui_mode: UIModeEnum = Field(
        UIModeEnum.SINGLE_AGENT,
        description="Front-end layout strategy.",
    )

    # Runtime
    llm: LLMSpec
    agents: list[AgentSpec] = Field(
        default_factory=list,
        description="Agents to ship. The first one is the default for single_agent UI mode "
        "unless ``default_agent_id`` is set.",
    )
    default_agent_id: str | None = Field(
        None, description="Override which agent is opened by default in single_agent UI mode."
    )

    # Assets
    knowledge_bases: list[str] = Field(
        default_factory=list,
        description="Knowledge base IDs to seed (rag/full only).",
    )
    extra_paths: list[str] = Field(
        default_factory=list,
        description="Additional repo-relative paths to copy verbatim into the package.",
    )

    # Config
    env_overrides: EnvOverrides = Field(default_factory=EnvOverrides)

    # Forward compatibility — packager will copy as-is into blueprint.lock.yaml
    extra: dict[str, Any] = Field(default_factory=dict)

    # ── Validation ──────────────────────────────────────────────────────

    @field_validator("name")
    @classmethod
    def _name_slug(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            raise ValueError(
                "name must be lowercase, start with a letter, "
                "use only [a-z0-9-], and be 2..50 chars long"
            )
        return v

    @field_validator("default_agent_id")
    @classmethod
    def _default_agent_exists(cls, v: str | None, info: Any) -> str | None:
        if v is None:
            return v
        agents = info.data.get("agents") or []
        if not any(a.id == v for a in agents):
            raise ValueError(f"default_agent_id={v!r} not found in agents[]")
        return v

    # ── Helpers ─────────────────────────────────────────────────────────

    def resolved_default_agent_id(self) -> str | None:
        if self.default_agent_id:
            return self.default_agent_id
        return self.agents[0].id if self.agents else None


# ── Loader ──────────────────────────────────────────────────────────────────


def load_blueprint(path: str | Path) -> Blueprint:
    """Load a blueprint from a YAML or JSON file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Blueprint file must be a mapping at the root: {p}")
    return Blueprint.model_validate(data)
