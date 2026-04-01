"""
GOV-EXP-001: A/B Execution Variant Tracker

Collects per-request thinking time telemetry for:
  - monolithic: one LLM call per tool-loop iteration
  - react: distributed Think→Act→Observe steps

Results are appended to a JSONL file for offline analysis.
A lightweight in-memory summary is also available via `get_summary()`.

Usage in swarm.py (at the end of _create_agent_node):
    from app.services.evaluation.ab_tracker import ab_tracker
    ab_tracker.record(...)
"""

import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock

from loguru import logger

# Path for JSONL log — lives alongside the backend logs
_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_AB_LOG_FILE = _LOG_DIR / "ab_execution_experiment.jsonl"


@dataclass
class ABRecord:
    """One data point from a single agent invocation."""
    timestamp: float
    conversation_id: str
    agent_name: str
    execution_variant: str      # "monolithic" | "react"
    total_think_ms: float       # sum of all LLM call durations
    num_llm_calls: int          # number of discrete LLM calls made
    avg_think_ms_per_call: float
    max_think_ms: float         # longest single LLM call
    min_think_ms: float         # shortest single LLM call
    quality_score: float = -1.0 # filled in by reflection if available


class ABTracker:
    """
    Thread-safe A/B experiment tracker for execution variant telemetry.
    """

    def __init__(self) -> None:
        self._records: list[ABRecord] = []
        self._lock = Lock()

        # Ensure log directory exists
        _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # ─── Recording ────────────────────────────────────────────────────────────

    def record(
        self,
        conversation_id: str,
        agent_name: str,
        execution_variant: str,
        thinking_times_ms: list[float],
        quality_score: float = -1.0,
    ) -> None:
        """Record one agent invocation's telemetry."""
        if not thinking_times_ms:
            return

        rec = ABRecord(
            timestamp=time.time(),
            conversation_id=conversation_id,
            agent_name=agent_name,
            execution_variant=execution_variant,
            total_think_ms=sum(thinking_times_ms),
            num_llm_calls=len(thinking_times_ms),
            avg_think_ms_per_call=sum(thinking_times_ms) / len(thinking_times_ms),
            max_think_ms=max(thinking_times_ms),
            min_think_ms=min(thinking_times_ms),
            quality_score=quality_score,
        )

        with self._lock:
            self._records.append(rec)
            self._append_to_file(rec)

        logger.info(
            f"📊 [AB Tracker] {execution_variant} | {agent_name} | "
            f"total={rec.total_think_ms:.0f}ms | calls={rec.num_llm_calls} | "
            f"avg={rec.avg_think_ms_per_call:.0f}ms/call"
        )

    def _append_to_file(self, rec: ABRecord) -> None:
        try:
            with _AB_LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(rec)) + "\n")
        except Exception as e:
            logger.warning(f"⚠️ [AB Tracker] Failed to write log: {e}")

    # ─── Analysis ─────────────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """
        Returns a statistical summary for each variant.

        Example output:
        {
          "monolithic": {"count": 42, "avg_total_ms": 1800, "avg_calls": 1.2, ...},
          "react":      {"count": 38, "avg_total_ms": 950,  "avg_calls": 3.1, ...},
          "winner": "react",
          "thinking_time_reduction_pct": 47.2
        }
        """
        with self._lock:
            records = list(self._records)

        if not records:
            return {"status": "no data yet"}

        groups: dict[str, list[ABRecord]] = defaultdict(list)
        for r in records:
            groups[r.execution_variant].append(r)

        stats = {}
        for variant, recs in groups.items():
            totals = [r.total_think_ms for r in recs]
            calls = [r.num_llm_calls for r in recs]
            scores = [r.quality_score for r in recs if r.quality_score >= 0]

            stats[variant] = {
                "count": len(recs),
                "avg_total_think_ms": round(sum(totals) / len(totals), 1),
                "median_total_think_ms": round(sorted(totals)[len(totals) // 2], 1),
                "p95_total_think_ms": round(sorted(totals)[int(len(totals) * 0.95)], 1),
                "avg_llm_calls": round(sum(calls) / len(calls), 2),
                "avg_quality_score": round(sum(scores) / len(scores), 3) if scores else None,
            }

        # Determine winner by total thinking time (lower = better)
        result = {"variants": stats}
        if "monolithic" in stats and "react" in stats:
            mono_ms = stats["monolithic"]["avg_total_think_ms"]
            react_ms = stats["react"]["avg_total_think_ms"]
            winner = "react" if react_ms < mono_ms else "monolithic"
            reduction_pct = abs(mono_ms - react_ms) / max(mono_ms, 1) * 100
            result["winner"] = winner
            result["thinking_time_delta_ms"] = round(mono_ms - react_ms, 1)
            result["thinking_time_reduction_pct"] = round(reduction_pct, 1)

        return result

    def load_from_file(self) -> int:
        """
        Load historical records from JSONL log file into memory.
        Returns count of records loaded.
        """
        if not _AB_LOG_FILE.exists():
            return 0
        loaded = 0
        with self._lock:
            try:
                with _AB_LOG_FILE.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            self._records.append(ABRecord(**data))
                            loaded += 1
            except Exception as e:
                logger.warning(f"⚠️ [AB Tracker] Failed to load log: {e}")
        logger.info(f"📂 [AB Tracker] Loaded {loaded} historical records from {_AB_LOG_FILE}")
        return loaded


# Module-level singleton
ab_tracker = ABTracker()
