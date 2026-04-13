"""
GOV-002: Routing Watchdog + Tier Escalation.

Monitors per-tier LLM failure rates via a sliding window and automatically
escalates to the next-higher ModelTier when the failure rate exceeds a
configurable threshold.  After a cooldown period, the watchdog attempts to
revert to the original tier (circuit recovery).

Usage — LLMRouter integration::

    # In get_model(), apply escalation transparently:
    effective_tier = routing_watchdog.get_effective_tier(requested_tier)

    # After a model call succeeds or fails:
    routing_watchdog.record(tier=original_tier, success=not error)

Observability::

    status = routing_watchdog.status()
    # Returns dict[tier_name, WatchdogStatus] for each tier.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import NamedTuple

from loguru import logger

from app.agents.schemas import ModelTier

# ──────────────────────────────────────────────────────────────────────────────
#  Escalation policy
# ──────────────────────────────────────────────────────────────────────────────

_ESCALATION_MAP: dict[ModelTier, ModelTier] = {
    ModelTier.SIMPLE:    ModelTier.MEDIUM,
    ModelTier.MEDIUM:    ModelTier.COMPLEX,
    ModelTier.COMPLEX:   ModelTier.REASONING,
    ModelTier.REASONING: ModelTier.REASONING,  # already at max
}

#: Rolling window size (events per tier).
_WINDOW_SIZE: int = 20

#: Failure rate (0–1) that triggers escalation.  Default: 50 %.
_FAILURE_THRESHOLD: float = 0.50

#: Seconds before attempting to revert an escalated tier.
_COOLDOWN_SECONDS: float = 300.0


# ──────────────────────────────────────────────────────────────────────────────
#  Internal data structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _RoutingEvent:
    success: bool
    timestamp: float = field(default_factory=time.monotonic)


class _TierState:
    """Per-tier sliding-window state (thread-safe)."""

    def __init__(self) -> None:
        self._window: deque[_RoutingEvent] = deque(maxlen=_WINDOW_SIZE)
        self._lock = Lock()
        self.escalated_to: ModelTier | None = None
        self.escalated_at: float | None = None

    # ── public ──────────────────────────────────────────────────────────────

    def record(self, success: bool) -> None:
        with self._lock:
            self._window.append(_RoutingEvent(success=success))

    def failure_rate(self) -> float:
        if not self._window:
            return 0.0
        return sum(1 for e in self._window if not e.success) / len(self._window)

    def window_size(self) -> int:
        return len(self._window)

    def should_escalate(self) -> bool:
        return (
            self.escalated_to is None
            and self.window_size() >= _WINDOW_SIZE // 2   # need ≥ half window
            and self.failure_rate() >= _FAILURE_THRESHOLD
        )

    def cooldown_elapsed(self) -> bool:
        return (
            self.escalated_at is not None
            and time.monotonic() - self.escalated_at >= _COOLDOWN_SECONDS
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────────────────────

class WatchdogStatus(NamedTuple):
    """Snapshot of a single tier's watchdog state (for observability)."""

    failure_rate: float
    window_size: int
    escalated_to: str | None       # None means no active escalation
    escalated_since: float | None  # monotonic timestamp or None


class RoutingWatchdog:
    """
    GOV-002: Sliding-window failure tracker that automatically escalates
    under-performing ModelTiers to the next-higher tier.

    Thread-safe; designed as a module-level singleton.
    """

    def __init__(self) -> None:
        self._states: dict[ModelTier, _TierState] = {t: _TierState() for t in ModelTier}

    # ── Core API ─────────────────────────────────────────────────────────────

    def record(self, tier: ModelTier, success: bool) -> None:
        """
        Record the outcome of a model call for the given tier.

        - Successful calls reset an escalation when the cooldown has elapsed.
        - Failed calls may trigger escalation if the failure threshold is crossed.
        """
        state = self._states[tier]
        state.record(success)

        if success:
            # Attempt recovery after cooldown
            if state.escalated_to and state.cooldown_elapsed():
                logger.info(
                    f"🔄 [RoutingWatchdog] {tier.value} recovery: "
                    f"cooldown elapsed — reverting from {state.escalated_to.value}."
                )
                state.escalated_to = None
                state.escalated_at = None
        else:
            # Check if escalation should be triggered
            if state.should_escalate():
                target = _ESCALATION_MAP[tier]
                if target != tier:
                    state.escalated_to = target
                    state.escalated_at = time.monotonic()
                    logger.warning(
                        f"⚡ [RoutingWatchdog] Tier '{tier.value}' failure rate "
                        f"{state.failure_rate():.0%} ≥ {_FAILURE_THRESHOLD:.0%} — "
                        f"escalating to '{target.value}'."
                    )

    def get_effective_tier(self, requested_tier: ModelTier) -> ModelTier:
        """
        Return the actual tier to use, applying any active escalation.
        If the cooldown has elapsed, clears escalation and returns the
        original tier.
        """
        state = self._states[requested_tier]
        if state.escalated_to:
            if state.cooldown_elapsed():
                logger.info(
                    f"🔄 [RoutingWatchdog] {requested_tier.value} cooldown elapsed "
                    f"— reverting escalation from {state.escalated_to.value}."
                )
                state.escalated_to = None
                state.escalated_at = None
                return requested_tier
            return state.escalated_to
        return requested_tier

    # ── Observability ────────────────────────────────────────────────────────

    def status(self) -> dict[str, WatchdogStatus]:
        """Return per-tier watchdog status for admin API / metrics."""
        return {
            tier.value: WatchdogStatus(
                failure_rate=round(state.failure_rate(), 3),
                window_size=state.window_size(),
                escalated_to=state.escalated_to.value if state.escalated_to else None,
                escalated_since=state.escalated_at,
            )
            for tier, state in self._states.items()
        }

    def reset(self, tier: ModelTier) -> None:
        """Manually clear escalation state for a tier (admin / test use)."""
        state = self._states[tier]
        state.escalated_to = None
        state.escalated_at = None
        state._window.clear()
        logger.info(f"🔧 [RoutingWatchdog] Tier '{tier.value}' state reset manually.")


# ──────────────────────────────────────────────────────────────────────────────
#  Module-level singleton
# ──────────────────────────────────────────────────────────────────────────────

routing_watchdog = RoutingWatchdog()
