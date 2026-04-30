"""
Semantic Identifier Mapping (Anthropic 2.1H).

Why
---
LLMs hallucinate when they have to copy long opaque IDs (UUIDs, ES doc
ids, hex hashes). They drop characters, swap digits, or invent
plausible-looking IDs that do not exist. The fix is to expose a short,
human-meaningful alias to the model and translate back to the real ID
on the way in.

Design
------
- **Sticky aliases**: once a raw ID is mapped, it always resolves to
  the same alias (idempotent across calls and processes within the
  current run). This is what keeps the model's references stable.
- **Bucketed counters**: aliases look like ``doc-rfc2119-1`` /
  ``doc-3`` — a kind prefix, an optional slug derived from a hint
  (filename, title), and a 1-based counter scoped to the slug bucket.
  Short, typeable, and meaningful at a glance.
- **Round-trip resolution**: ``resolve(alias_or_raw)`` accepts either
  the alias or the original raw ID, so tools can be called with
  whichever form the agent has at hand without breaking compatibility.
- **Bounded memory**: an LRU cap evicts the oldest aliases to keep the
  registry from growing unboundedly during long-lived processes.

This is intentionally a process-wide singleton (not per-conversation):
the model's loss function for ID hallucination doesn't care about
session boundaries, and a global registry maximises alias stability
when the same document reappears in different conversations.
"""

from __future__ import annotations

import re
import threading
from collections import OrderedDict
from typing import Optional

# Hard cap on registry entries — eviction is FIFO/LRU on the alias side.
_MAX_ENTRIES = 5000

# Slug rules: keep ascii alnum + dash, collapse runs, cap length.
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, *, max_len: int = 24) -> str:
    if not text:
        return ""
    # Strip path / extension noise from filenames first.
    text = text.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    text = text.rsplit(".", 1)[0] if "." in text else text
    text = text.lower()
    text = _SLUG_STRIP.sub("-", text).strip("-")
    return text[:max_len].rstrip("-")


class SemanticIdMapper:
    """Bidirectional alias <-> raw-id registry, thread-safe."""

    def __init__(self, *, max_entries: int = _MAX_ENTRIES):
        self._raw_to_alias: "OrderedDict[str, str]" = OrderedDict()
        self._alias_to_raw: dict[str, str] = {}
        self._bucket_counters: dict[str, int] = {}
        self._lock = threading.Lock()
        self._max_entries = max_entries

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------
    def alias_for(
        self,
        raw_id: str,
        *,
        kind: str = "doc",
        hint: Optional[str] = None,
    ) -> str:
        """Return the (sticky) alias for a raw ID, creating it if needed."""
        if not raw_id:
            return raw_id
        raw_id = str(raw_id)
        with self._lock:
            existing = self._raw_to_alias.get(raw_id)
            if existing is not None:
                # Touch for LRU.
                self._raw_to_alias.move_to_end(raw_id)
                return existing

            slug = _slugify(hint) if hint else ""
            bucket = f"{kind}-{slug}" if slug else kind
            n = self._bucket_counters.get(bucket, 0) + 1
            self._bucket_counters[bucket] = n
            alias = f"{bucket}-{n}"

            # Defensive: if alias collides (shouldn't, but external mutation
            # is possible), fall back to a longer, hash-tagged form.
            if alias in self._alias_to_raw:
                tag = f"{abs(hash(raw_id)) % 0xFFFF:x}"
                alias = f"{bucket}-{n}-{tag}"

            self._raw_to_alias[raw_id] = alias
            self._alias_to_raw[alias] = raw_id

            # LRU eviction.
            while len(self._raw_to_alias) > self._max_entries:
                old_raw, old_alias = self._raw_to_alias.popitem(last=False)
                self._alias_to_raw.pop(old_alias, None)

            return alias

    def resolve(self, alias_or_raw: str) -> str:
        """Translate an alias back to its raw ID. Pass-through for unknown / raw."""
        if not alias_or_raw:
            return alias_or_raw
        return self._alias_to_raw.get(str(alias_or_raw), str(alias_or_raw))

    def is_alias(self, value: str) -> bool:
        return bool(value) and str(value) in self._alias_to_raw

    # Useful for tests / introspection.
    def stats(self) -> dict:
        with self._lock:
            return {
                "entries": len(self._raw_to_alias),
                "buckets": dict(self._bucket_counters),
            }

    def clear(self) -> None:
        with self._lock:
            self._raw_to_alias.clear()
            self._alias_to_raw.clear()
            self._bucket_counters.clear()


# --------------------------------------------------------------------------
# Singleton accessor — one mapper per tenant, so aliases never collide
# across organisations. Reads ``app.core.tenant_context`` to resolve the
# active tenant when none is passed explicitly.
# --------------------------------------------------------------------------
_mappers: dict[str, "SemanticIdMapper"] = {}
_mapper_lock = threading.Lock()


def get_semantic_id_mapper(tenant_id: Optional[str] = None) -> SemanticIdMapper:
    if tenant_id is None:
        try:
            from app.core.tenant_context import get_current_tenant

            tenant_id = get_current_tenant()
        except Exception:  # noqa: BLE001
            tenant_id = "default"
    key = tenant_id or "default"
    mapper = _mappers.get(key)
    if mapper is None:
        with _mapper_lock:
            mapper = _mappers.get(key)
            if mapper is None:
                mapper = SemanticIdMapper()
                _mappers[key] = mapper
    return mapper
