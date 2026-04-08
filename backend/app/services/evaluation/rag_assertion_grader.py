"""
RAG Assertion Grader — Strong Rule-Based Integrity Checks for RAG Responses.

Two mandatory assertions that LLM graders cannot override:
  1. Citation Format: When KB results exist, response MUST contain [N] style markers.
  2. "Not Found" Declaration: When KB is empty, response MUST acknowledge the absence.

These are hard rules (HardBlock), not soft scoring opinions.
"""

import re
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_trace_logger

logger = get_trace_logger(__name__)


@dataclass
class AssertionViolation:
    rule_id: str
    description: str
    penalty: float  # score cap to apply to the offending grader aspect


class RagAssertionResult:
    """Result from the RAG integrity assertion checks."""

    def __init__(self):
        self.violations: list[AssertionViolation] = []

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0

    def add_violation(self, rule_id: str, description: str, penalty: float = 0.2):
        self.violations.append(AssertionViolation(rule_id, description, penalty))

    def get_penalty_for_aspect(self, aspect: str) -> float | None:
        """Return the harshest penalty score cap for a given grader aspect, if any."""
        if aspect == "citation_accuracy":
            for v in self.violations:
                if v.rule_id == "CITE-001":
                    return v.penalty
        if aspect == "accuracy":
            for v in self.violations:
                if v.rule_id == "CITE-002":
                    return v.penalty
        return None


# Regex that matches properly formatted citation markers like [1], [12], [3]
_CITATION_PATTERN = re.compile(r"\[\d+\]")

# Keywords indicating a "not found" response from the assistant
_NOT_FOUND_PHRASES = frozenset([
    "未找到", "没有找到", "找不到", "不在知识库", "知识库中没有",
    "not found", "no relevant", "couldn't find", "could not find",
    "don't have information", "do not have information", "no information",
    "sorry", "抱歉",
])

# Context strings that indicate an empty knowledge base search
_EMPTY_CONTEXT_MARKERS = frozenset([
    "no relevant information found",
    "no results",
    "empty",
])


def _context_is_empty(context: str) -> bool:
    lowered = context.strip().lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in _EMPTY_CONTEXT_MARKERS)


def _response_has_citations(response: Any) -> bool:
    if not isinstance(response, str):
        if hasattr(response, "model_dump_json"):
            response = response.model_dump_json()
        else:
            response = str(response)
    return bool(_CITATION_PATTERN.search(response))


def _response_acknowledges_not_found(response: Any) -> bool:
    if not isinstance(response, str):
        if hasattr(response, "model_dump_json"):
            response = response.model_dump_json()
        else:
            response = str(response)
    lowered = response.lower()
    return any(phrase in lowered for phrase in _NOT_FOUND_PHRASES)


class RagAssertionGrader:
    """
    Hard rule asserter for RAG response quality.

    Designed to be called BEFORE (or alongside) LLM-based graders in the
    MultiGrader pipeline. Any violations are used to cap the scores of the
    corresponding LLM grader aspects.
    """

    def check(self, query: str, response: Any, context: str = "") -> RagAssertionResult:
        """
        Run all RAG assertion checks and return violations list.

        Args:
            query:    The user's original query.
            response: The AI assistant's response text (or structured result).
            context:  The retrieved knowledge context injected into the prompt.
                      Empty string means the KB returned no results.

        Returns:
            RagAssertionResult with zero or more violations.
        """
        result = RagAssertionResult()
        empty_context = _context_is_empty(context)

        # Normalize response for length check
        resp_str = ""
        if isinstance(response, str):
            resp_str = response
        elif hasattr(response, "model_dump_json"):
            resp_str = response.model_dump_json()
        else:
            resp_str = str(response)

        # --- CITE-001: Must cite when KB results exist ---
        if not empty_context and not _response_has_citations(response):
            msg = (
                "Response is missing mandatory [N] citation markers even though KB context was provided. "
                "Every sentence grounded in retrieved knowledge MUST reference its source(s) with [1], [2], etc."
            )
            logger.warning(f"🚩 [RagAssert] CITE-001 violation: {msg[:80]}")
            result.add_violation("CITE-001", msg, penalty=0.2)

        # --- CITE-002: Must NOT answer confidently when KB is empty ---
        if empty_context and not _response_acknowledges_not_found(response):
            # Only flag if the response is suspiciously long (not just a clarification)
            if len(resp_str.strip()) > 80:
                msg = (
                    "KB context was empty but response does not declare 'not found'. "
                    "This suggests the model is hallucinating from parametric memory "
                    "instead of stating that the knowledge base has no relevant content."
                )
                logger.warning(f"🚩 [RagAssert] CITE-002 violation: {msg[:80]}")
                result.add_violation("CITE-002", msg, penalty=0.1)

        return result


# Module-level singleton
rag_assertion_grader = RagAssertionGrader()
