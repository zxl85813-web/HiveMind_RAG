"""
Deterministic hard-rule checks for Hybrid Reflection.

These checks are intentionally *non-LLM* so they cannot be flattered or
hallucinated past. They run alongside the LLM graders and act as a
**veto gate**: if any rule trips, the verdict is forced to ``FAIL``
regardless of how well the LLM judges the response.

This implements the Anthropic guidance "don't let the same model be
both player and referee" — we keep the LLM judge for nuance, but back
it with code-based assertions for safety/format/citation correctness.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

# Tokens that indicate a tool-call protocol bled into the user-facing
# response (mirrors ``CacheService.POISON_TOKENS`` so we never ship them).
_POISON_TOKENS = (
    "tool_calls_begin",
    "tool_sep",
    "tool_call_end",
    "tool▁calls",
    "tool▁sep",
    "<|tool_call|>",
)

# Common PII patterns. Conservative on purpose — false positives here
# only force a re-write, not a system error.
_PII_PATTERNS = {
    "phone_cn": re.compile(r"\b1[3-9]\d{9}\b"),
    "id_card_cn": re.compile(r"\b\d{17}[\dXx]\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "api_key_like": re.compile(r"\b(?:sk-|api[_-]?key[\"':=\s]+)[A-Za-z0-9_\-]{16,}", re.IGNORECASE),
}

# Citation tag pattern emitted by KnowledgeResponse.to_prompt_context().
_CITATION_TAG = re.compile(r"\[\^([\w:#\-./]+)\]")


@dataclass
class HardRuleResult:
    """Outcome of a single deterministic check."""

    name: str
    passed: bool
    severity: str  # "veto" | "warn"
    reason: str = ""

    @property
    def is_veto_failure(self) -> bool:
        return (not self.passed) and self.severity == "veto"


@dataclass
class HardRuleReport:
    """Aggregate over all hard rules."""

    results: List[HardRuleResult] = field(default_factory=list)

    @property
    def vetoed(self) -> bool:
        return any(r.is_veto_failure for r in self.results)

    @property
    def failures(self) -> List[HardRuleResult]:
        return [r for r in self.results if not r.passed]

    def summary(self) -> str:
        if not self.results:
            return "no hard rules ran"
        if not self.failures:
            return f"all {len(self.results)} hard rules passed"
        bits = [
            f"{r.name}={'VETO' if r.severity == 'veto' else 'warn'}"
            for r in self.failures
        ]
        return f"{len(self.failures)}/{len(self.results)} failed: " + ", ".join(bits)


# --------------------------------------------------------------------------
# Individual rules
# --------------------------------------------------------------------------
def _check_non_empty(response: str) -> HardRuleResult:
    return HardRuleResult(
        name="non_empty",
        passed=bool(response and response.strip()),
        severity="veto",
        reason="response is empty",
    )


def _check_no_protocol_leak(response: str) -> HardRuleResult:
    leaked = [tok for tok in _POISON_TOKENS if tok in response]
    return HardRuleResult(
        name="no_protocol_leak",
        passed=not leaked,
        severity="veto",
        reason=f"leaked tokens: {', '.join(leaked)}" if leaked else "",
    )


def _check_json_validity(response: str) -> HardRuleResult:
    """Any ```json fenced block must parse."""
    blocks = re.findall(r"```json\s*(.*?)```", response, flags=re.DOTALL)
    bad: List[str] = []
    for block in blocks:
        try:
            json.loads(block)
        except json.JSONDecodeError as e:
            bad.append(f"line {e.lineno}: {e.msg}")
    return HardRuleResult(
        name="json_blocks_valid",
        passed=not bad,
        severity="veto" if bad else "veto",
        reason="; ".join(bad),
    )


def _check_citations(response: str, known_ids: Optional[List[str]] = None) -> HardRuleResult:
    """Citation tags must reference ids the gateway actually produced.

    If we don't have a citation set (``known_ids is None``), we skip;
    only flag *unknown* references, not their absence.
    """
    if known_ids is None:
        return HardRuleResult(
            name="citations_resolved",
            passed=True,
            severity="warn",
        )
    used = set(_CITATION_TAG.findall(response))
    if not used:
        return HardRuleResult(
            name="citations_resolved",
            passed=True,
            severity="warn",
        )
    known = set(known_ids)
    unknown = sorted(used - known)
    return HardRuleResult(
        name="citations_resolved",
        passed=not unknown,
        severity="veto",
        reason=f"unknown citations: {', '.join(unknown[:5])}" if unknown else "",
    )


def _check_pii(response: str) -> HardRuleResult:
    hits: List[str] = []
    for label, pat in _PII_PATTERNS.items():
        if pat.search(response):
            hits.append(label)
    return HardRuleResult(
        name="no_pii_leak",
        passed=not hits,
        severity="veto",
        reason=f"detected: {', '.join(hits)}" if hits else "",
    )


def _check_length(response: str, min_chars: int = 10, max_chars: int = 24000) -> HardRuleResult:
    n = len(response.strip())
    if n < min_chars:
        return HardRuleResult(
            name="length",
            passed=False,
            severity="veto",
            reason=f"too short ({n} < {min_chars})",
        )
    if n > max_chars:
        return HardRuleResult(
            name="length",
            passed=False,
            severity="warn",
            reason=f"too long ({n} > {max_chars})",
        )
    return HardRuleResult(name="length", passed=True, severity="warn")


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
def evaluate_hard_rules(
    response: str,
    *,
    known_citation_ids: Optional[List[str]] = None,
) -> HardRuleReport:
    """Run all deterministic checks and return an aggregate report."""
    response = response or ""
    return HardRuleReport(
        results=[
            _check_non_empty(response),
            _check_no_protocol_leak(response),
            _check_json_validity(response),
            _check_pii(response),
            _check_length(response),
            _check_citations(response, known_citation_ids),
        ]
    )
