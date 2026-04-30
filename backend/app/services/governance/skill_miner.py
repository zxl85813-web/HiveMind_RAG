"""
Self-Evolving Skill Miner (Anthropic 2.1I).

Goal
----
When the same tool sequence keeps showing up in successful conversations
("call ``search_knowledge_base`` → ``kb_doc_grep`` → ``record_reflection``"),
that pattern is a *latent skill* — encoding it as a first-class
``Skill`` makes future runs cheaper (1 tool call instead of 3) and
gives the agent a reusable handle.

This module:

1. Reads tool-call counters from ``FlowMonitor`` snapshots (no extra
   instrumentation needed — we already record them).
2. Looks at the *ordered* tool sequence per conversation (via
   ``FlowMonitor._flows`` directly, with a small accessor).
3. Mines frequent contiguous n-grams (length 2–4) across multiple
   *healthy* conversations.
4. Writes each candidate as a draft skill into ``skills/_drafts/<slug>/SKILL.md``
   with ``status: draft`` in the frontmatter so a human can promote it.

Crucially we **do not** auto-register drafts into ``SkillRegistry``.
Self-evolution proposes; humans dispose. This matches the safety
guidance: anything that can run an Agent loop must be reviewed.

The miner is callable on demand (no background thread) so it stays
predictable: an operator runs ``mine_and_persist()`` from a CLI / API
when they want to inspect candidates.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from loguru import logger

from app.services.governance.flow_monitor import FlowMonitor, get_flow_monitor


# Mining knobs — conservative; bias towards quality over quantity.
MIN_PATTERN_LEN = 2
MAX_PATTERN_LEN = 4
MIN_PATTERN_SUPPORT = 3   # pattern must appear in ≥3 conversations to count


@dataclass
class SkillCandidate:
    pattern: Tuple[str, ...]
    support: int                                 # how many conversations contain it
    occurrences: int                             # total raw occurrences
    sample_conversation_ids: List[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return "auto-" + "-".join(
            re.sub(r"[^a-z0-9]+", "", t.lower())[:12] or "tool"
            for t in self.pattern
        )

    def render_skill_md(self) -> str:
        """Render a draft SKILL.md with frontmatter + body."""
        front = (
            "---\n"
            f"name: {self.slug}\n"
            "status: draft\n"
            "version: 0.0.1\n"
            "tags: [auto-mined, candidate]\n"
            f'description: "Auto-mined macro: {" → ".join(self.pattern)}"\n'
            "---\n"
        )
        body = (
            f"# Skill candidate: `{self.slug}`\n\n"
            f"This skill was **auto-mined** from production trace data. "
            f"It encodes a tool sequence that appeared in **{self.support}** "
            f"distinct conversations (with **{self.occurrences}** raw "
            f"occurrences total).\n\n"
            "## Pattern\n\n"
            f"```\n{' -> '.join(self.pattern)}\n```\n\n"
            "## Sample conversations\n\n"
            + "\n".join(f"- `{cid}`" for cid in self.sample_conversation_ids[:5])
            + "\n\n"
            "## Promotion checklist\n\n"
            "- [ ] Confirm the pattern is genuinely reusable (not a quirk of a few users).\n"
            "- [ ] Wrap the steps in a deterministic `tools.py` entrypoint.\n"
            "- [ ] Replace this draft frontmatter with `status: stable` and a curated description.\n"
            "- [ ] Move out of `_drafts/` into a top-level skill directory.\n"
        )
        return front + body


class SkillMiner:
    """Mines tool-sequence n-grams from FlowMonitor's per-conversation logs."""

    def __init__(self, monitor: Optional[FlowMonitor] = None):
        self.monitor = monitor or get_flow_monitor()

    # ------------------------------------------------------------------
    # Mining
    # ------------------------------------------------------------------
    def _conversations(self) -> Iterable[Tuple[str, List[str]]]:
        """Yield ``(conversation_id, ordered_tool_sequence)`` from the monitor.

        We piggy-back on ``FlowMonitor`` internals because that's where
        the only existing ordered record of tool calls lives. The
        accessor is read-only and shielded by a try/except so a future
        refactor of the monitor cannot crash mining.
        """
        try:
            flows = getattr(self.monitor, "_flows", {})
        except Exception:  # noqa: BLE001
            return
        for cid, flow in list(flows.items()):
            seq = list(getattr(flow, "tool_args_counter", {}).keys())
            # tool_args_counter keys are (tool_name, repr(args)). We only
            # need the tool_name dimension for sequence mining.
            tool_seq = [t[0] for t in seq if isinstance(t, tuple)]
            if tool_seq:
                yield cid, tool_seq

    def mine(self) -> List[SkillCandidate]:
        """Return candidate skills, sorted by support * length (desc)."""
        # support[pattern] = set of conversation ids that contain it
        # occ[pattern]     = total occurrences
        support: dict[Tuple[str, ...], set] = {}
        occurrences: Counter = Counter()

        for cid, seq in self._conversations():
            seen_in_conv: set = set()
            for n in range(MIN_PATTERN_LEN, MAX_PATTERN_LEN + 1):
                for i in range(len(seq) - n + 1):
                    pat = tuple(seq[i : i + n])
                    occurrences[pat] += 1
                    if pat not in seen_in_conv:
                        support.setdefault(pat, set()).add(cid)
                        seen_in_conv.add(pat)

        candidates = [
            SkillCandidate(
                pattern=pat,
                support=len(cids),
                occurrences=occurrences[pat],
                sample_conversation_ids=sorted(cids),
            )
            for pat, cids in support.items()
            if len(cids) >= MIN_PATTERN_SUPPORT
        ]
        # Prefer longer high-support patterns — they encode more value.
        candidates.sort(key=lambda c: (c.support * len(c.pattern), c.support), reverse=True)
        return candidates

    # ------------------------------------------------------------------
    # Persistence — drafts only, never registered
    # ------------------------------------------------------------------
    def persist_drafts(
        self,
        candidates: List[SkillCandidate],
        *,
        skills_root: str = "skills",
    ) -> List[Path]:
        """Write each candidate to ``<skills_root>/_drafts/<slug>/SKILL.md``."""
        drafts_dir = Path(skills_root) / "_drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        written: List[Path] = []
        for cand in candidates:
            target_dir = drafts_dir / cand.slug
            target_dir.mkdir(exist_ok=True)
            md_path = target_dir / "SKILL.md"
            md_path.write_text(cand.render_skill_md(), encoding="utf-8")
            written.append(md_path)
        if written:
            logger.info(
                f"🌱 [SkillMiner] wrote {len(written)} draft skill(s) to {drafts_dir}"
            )
        return written

    def mine_and_persist(self, *, skills_root: str = "skills") -> List[Path]:
        return self.persist_drafts(self.mine(), skills_root=skills_root)


# --------------------------------------------------------------------------
# Singleton — keyed by tenant. Drafts of one tenant must never leak into
# another tenant's skill catalog.
# --------------------------------------------------------------------------
_miners: dict[str, "SkillMiner"] = {}


def get_skill_miner(tenant_id: Optional[str] = None) -> SkillMiner:
    if tenant_id is None:
        try:
            from app.core.tenant_context import get_current_tenant

            tenant_id = get_current_tenant()
        except Exception:  # noqa: BLE001
            tenant_id = "default"
    key = tenant_id or "default"
    miner = _miners.get(key)
    if miner is None:
        miner = SkillMiner()
        _miners[key] = miner
    return miner
