"""
Production Shadow Evaluations (Anthropic 2.1J).

Why
---
Production drift is silent: the model still answers, the user still
clicks "thumbs-up out of habit", and nothing alerts. Anthropic's
remedy is to run **shadow evaluations** — sampled, *non-blocking*
re-grading of real traffic so the team can:

- compare ground-truth user feedback vs. automated graders,
- catch infrastructure-induced randomness (timeouts, truncation,
  partial RAG recall),
- detect "model understanding decay" between deployment rings.

Design
------
- **Probabilistic sampling** (default 5%): cheap to leave on in prod.
- **Fully async, fire-and-forget**: ``asyncio.create_task`` so the
  user-facing latency is unchanged. Failures are swallowed with a
  warning — shadow evals must never fail a real request.
- **Persistence** via ``audit_service.log_event`` (already wired into
  the existing audit trail), so reports show up in the same store ops
  already monitor.
- **Ring-aware**: when called from a Rainbow-routed conversation we
  stamp the ring name on the report, enabling per-ring quality
  comparisons (the whole point of running canaries).

This module is *additive*: it never blocks, never throws to the
caller, and is a no-op when ``ENABLE_SHADOW_EVALS=False``.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from dataclasses import dataclass
from typing import List, Optional

from loguru import logger

from app.services.evaluation.multi_grader import MultiGraderEval


def _flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


SAMPLE_RATE = float(os.environ.get("SHADOW_EVAL_SAMPLE_RATE", "0.05"))
ENABLED = _flag("ENABLE_SHADOW_EVALS", default=True)


@dataclass
class ShadowEvalReport:
    conversation_id: str
    ring: Optional[str]
    composite_score: float
    verdict: str
    hard_rule_summary: str
    hard_rule_vetoed: bool
    elapsed_ms: float


class ShadowEvalSampler:
    """Sampled background grader for production traffic.

    Use ``maybe_evaluate(...)`` from request-finishing code paths. It
    decides whether to sample, schedules a background task, and
    returns immediately.
    """

    def __init__(
        self,
        *,
        sample_rate: float = SAMPLE_RATE,
        enabled: bool = ENABLED,
    ):
        self.sample_rate = max(0.0, min(1.0, float(sample_rate)))
        self.enabled = bool(enabled)
        self._evaluator = MultiGraderEval()

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------
    def should_sample(self, *, force: bool = False) -> bool:
        if not self.enabled:
            return False
        if force:
            return True
        return random.random() < self.sample_rate

    def maybe_evaluate(
        self,
        *,
        conversation_id: str,
        query: str,
        response: str,
        context: str = "",
        known_citation_ids: Optional[List[str]] = None,
        ring: Optional[str] = None,
        force: bool = False,
    ) -> Optional["asyncio.Task"]:
        """Schedule a shadow eval if the sampler decides to. Non-blocking.

        Returns the background ``asyncio.Task`` (mainly for tests) or
        ``None`` when not sampled. The task never raises into the caller.
        """
        if not self.should_sample(force=force):
            return None

        coro = self._evaluate_and_log(
            conversation_id=conversation_id,
            query=query,
            response=response,
            context=context,
            known_citation_ids=known_citation_ids,
            ring=ring,
        )
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (rare — sync caller). Fire on a fresh loop
            # in a background thread so we still don't block.
            import threading

            def _runner() -> None:
                try:
                    asyncio.run(coro)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"🕵️ ShadowEval thread failed: {e}")

            threading.Thread(target=_runner, daemon=True).start()
            return None
        return loop.create_task(coro)

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------
    async def _evaluate_and_log(
        self,
        *,
        conversation_id: str,
        query: str,
        response: str,
        context: str,
        known_citation_ids: Optional[List[str]],
        ring: Optional[str],
    ) -> None:
        start = time.time()
        try:
            result = await self._evaluator.evaluate(
                query=query,
                response=response,
                context=context,
                known_citation_ids=known_citation_ids,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"🕵️ ShadowEval failed for conv={conversation_id}: {e}")
            return

        report = ShadowEvalReport(
            conversation_id=conversation_id,
            ring=ring,
            composite_score=result.composite_score,
            verdict=result.verdict,
            hard_rule_summary=result.hard_rule_summary,
            hard_rule_vetoed=result.hard_rule_vetoed,
            elapsed_ms=(time.time() - start) * 1000,
        )

        log_line = (
            f"🕵️ shadow_eval conv={report.conversation_id} ring={report.ring or '-'} "
            f"verdict={report.verdict} score={report.composite_score:.2f} "
            f"hard_rules={report.hard_rule_summary} elapsed={report.elapsed_ms:.0f}ms"
        )
        if report.hard_rule_vetoed or report.verdict == "FAIL":
            logger.warning(log_line)
        else:
            logger.info(log_line)

        # Persist to audit if available — shadow eval reports become a
        # first-class observable signal.
        try:
            from app.services.audit_service import log_event  # type: ignore

            log_event(
                event_type="shadow_eval",
                payload={
                    "conversation_id": report.conversation_id,
                    "ring": report.ring,
                    "verdict": report.verdict,
                    "score": report.composite_score,
                    "hard_rule_summary": report.hard_rule_summary,
                    "hard_rule_vetoed": report.hard_rule_vetoed,
                    "elapsed_ms": report.elapsed_ms,
                },
            )
        except Exception:  # noqa: BLE001
            # audit_service may be optional in some deployments; we already
            # logged via loguru above so this is best-effort.
            pass


# --------------------------------------------------------------------------
# Per-tenant accessor — keep shadow eval samples isolated per tenant.
# --------------------------------------------------------------------------
import threading

_samplers: dict[str, "ShadowEvalSampler"] = {}
_sampler_lock = threading.Lock()


def get_shadow_eval_sampler(tenant_id: Optional[str] = None) -> ShadowEvalSampler:
    if not tenant_id:
        from app.core.tenant_context import get_current_tenant
        tenant_id = get_current_tenant()
    inst = _samplers.get(tenant_id)
    if inst is None:
        with _sampler_lock:
            inst = _samplers.get(tenant_id)
            if inst is None:
                inst = ShadowEvalSampler()
                _samplers[tenant_id] = inst
    return inst
