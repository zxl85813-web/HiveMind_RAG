"""
Semantic ID Mapper (2.1H)
==========================
Converts opaque database UUIDs to human-readable [0]name, [1]name indexed
identifiers in agent outputs, dramatically reducing model hallucination.

Problem: LLMs struggle with long UUIDs like "3f6a9c12-0b4e-4f87-a2d1-9e8f7c6b5a4d".
Solution: Map them to compact [0]name references in all agent tool outputs.

Usage:
    mapper = SemanticIDMapper()
    mapper.add("3f6a9c12-...", "Project Alpha KB")
    mapper.add("7b2e1f04-...", "Sales Docs KB")

    text = mapper.apply(some_text_with_uuids)
    # "[0]Project Alpha KB" instead of "3f6a9c12-..."

    # Format a list of items as an indexed table
    table = SemanticIDMapper.format_list(items, id_key="id", name_key="name")
    # "[0] Project Alpha KB  (id=3f6a9c12…)\n[1] Sales Docs KB  (id=7b2e1f04…)"

    # Resolve back to full UUID
    uuid = mapper.resolve("[0]", items, id_key="id")
"""

from __future__ import annotations

import re
from typing import Any


class SemanticIDMapper:
    """
    Bi-directional mapper between opaque UUIDs and [N]semantic-name references.

    Lifecycle:
      1. `add(uuid, label)` — register a mapping during a session.
      2. `apply(text)` — replace all known UUIDs in any text blob with [N]name.
      3. `resolve(token)` — convert [N] or partial UUID back to the full UUID.
    """

    def __init__(self) -> None:
        self._uuid_to_index: dict[str, int] = {}
        self._index_to_label: dict[int, str] = {}
        self._uuid_to_label: dict[str, str] = {}

    def add(self, uuid: str, label: str) -> int:
        """Register a UUID→label mapping and return the assigned index."""
        if uuid in self._uuid_to_index:
            return self._uuid_to_index[uuid]
        idx = len(self._uuid_to_index)
        self._uuid_to_index[uuid] = idx
        self._index_to_label[idx] = label
        self._uuid_to_label[uuid] = label
        return idx

    def apply(self, text: str) -> str:
        """Replace all registered UUIDs in text with [N]label tokens."""
        for uuid, idx in self._uuid_to_index.items():
            label = self._index_to_label[idx]
            text = text.replace(uuid, f"[{idx}]{label}")
        return text

    def resolve(self, token: str) -> str | None:
        """
        Resolve a [N] token or UUID prefix back to the full UUID.
        Returns None if not found.
        """
        # [N] index token
        m = re.fullmatch(r"\[(\d+)\].*", token.strip())
        if m:
            idx = int(m.group(1))
            for uuid, i in self._uuid_to_index.items():
                if i == idx:
                    return uuid
        # Partial UUID prefix
        for uuid in self._uuid_to_index:
            if uuid.startswith(token.strip()):
                return uuid
        return None

    # ------------------------------------------------------------------
    # Stateless helpers — no instance needed
    # ------------------------------------------------------------------

    @staticmethod
    def format_list(
        items: list[dict[str, Any]],
        id_key: str = "id",
        name_key: str = "name",
        extra_keys: list[str] | None = None,
    ) -> str:
        """
        Format a list of dicts as a compact indexed table.

        Example output:
            [0] Project Alpha KB  (id=3f6a9c12…)
            [1] Sales Docs KB     (id=7b2e1f04…)
        """
        lines: list[str] = []
        for idx, item in enumerate(items):
            uid = str(item.get(id_key, ""))
            uid_short = uid[:8] + "…" if len(uid) > 8 else uid
            name = str(item.get(name_key, uid_short))
            extras = ""
            if extra_keys:
                parts = [f"{k}={item[k]}" for k in extra_keys if k in item]
                if parts:
                    extras = "  " + ", ".join(parts)
            lines.append(f"[{idx}] {name}  (id={uid_short}){extras}")
        return "\n".join(lines)

    @staticmethod
    def resolve_from_list(
        token: str,
        items: list[dict[str, Any]],
        id_key: str = "id",
    ) -> str | None:
        """
        Resolve [N] or UUID-prefix to a full UUID from a list of dicts.
        Useful in tool-call handlers where the agent passed [0] instead of raw UUID.
        """
        m = re.fullmatch(r"\[(\d+)\].*", token.strip())
        if m:
            idx = int(m.group(1))
            if 0 <= idx < len(items):
                return str(items[idx].get(id_key))
        for item in items:
            uid = str(item.get(id_key, ""))
            if uid.startswith(token.strip()):
                return uid
        return None


# Module-level singleton for use across a single request/session.
# Call semantic_id_mapper.add() when generating lists, and
# semantic_id_mapper.apply() before injecting into LLM context.
semantic_id_mapper = SemanticIDMapper()
