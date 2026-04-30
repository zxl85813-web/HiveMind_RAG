"""
Observability Trace Analytics (Anthropic 2.1I).

Sits on top of ``FlowMonitor`` and turns its raw counters into actionable
*efficiency reports*. Where ``FlowMonitor`` says "this conversation
visited supervisor 8 times", ``TraceAnalyzer`` synthesises that into:

    {
      "verdict": "inefficient",
      "issues": [
        "supervisor_thrash: 8 supervisor visits with 2 agents touched",
        "tool_redundancy: search_knowledge_base called 6× with 2 unique args",
      ],
      "recommendations": [
        "increase supervisor temperature or revise routing prompt",
        "add result-caching wrapper around search_knowledge_base",
      ],
    }

Design
------
- **Pure analyser**, no IO of its own. Reads from ``FlowMonitor``
  snapshots; writes nothing back.
- **Heuristic-driven** — these are the same heuristics ops engineers
  develop manually after staring at traces. Codifying them gives every
  conversation a free trace review.
- Exposed via a tiny FastAPI router so dashboards and operators can
  pull a report by ``conversation_id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.governance.flow_monitor import FlowMonitor, get_flow_monitor


# Heuristic thresholds — calibrated against typical SwarmOrchestrator runs.
SUPERVISOR_THRASH_THRESHOLD = 5      # supervisor visits per conversation
REFLECTION_LOOP_THRESHOLD = 3        # reflections that didn't FINISH
TOOL_REDUNDANCY_THRESHOLD = 4        # same tool ≥4× this conversation
LOW_AGENT_DIVERSITY_RATIO = 0.4      # supervisor visits / unique agents


@dataclass
class TraceReport:
    conversation_id: str
    verdict: str = "healthy"   # "healthy" | "noisy" | "inefficient"
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    stats: Dict[str, object] = field(default_factory=dict)


class TraceAnalyzer:
    """Heuristic analyser over a ``FlowMonitor`` snapshot."""

    def __init__(self, monitor: Optional[FlowMonitor] = None):
        self.monitor = monitor or get_flow_monitor()

    def analyze(self, conversation_id: str) -> TraceReport:
        snap = self.monitor.snapshot(conversation_id)
        report = TraceReport(conversation_id=conversation_id, stats=snap)
        if not snap:
            report.verdict = "unknown"
            report.issues.append("no flow data for this conversation")
            return report

        node_visits: Dict[str, int] = snap.get("node_visits", {})  # type: ignore[assignment]
        tool_calls: Dict[str, int] = snap.get("tool_calls", {})  # type: ignore[assignment]
        anomaly_count: int = int(snap.get("anomaly_count") or 0)

        sup_visits = node_visits.get("supervisor", 0)
        refl_visits = node_visits.get("reflection", 0)
        agent_nodes = [
            (n, v) for n, v in node_visits.items()
            if n not in {"supervisor", "reflection", "pre_processor", "platform_action"}
        ]

        # 1. Supervisor thrash — too many supervisor turns relative to actual agent work.
        if sup_visits >= SUPERVISOR_THRASH_THRESHOLD:
            unique_agents = len(agent_nodes)
            ratio = (
                unique_agents / sup_visits if sup_visits else 1.0
            )
            if ratio < LOW_AGENT_DIVERSITY_RATIO:
                report.issues.append(
                    f"supervisor_thrash: {sup_visits} supervisor visits "
                    f"with only {unique_agents} unique agents touched"
                )
                report.recommendations.append(
                    "tighten supervisor prompt — it is re-planning instead of dispatching"
                )

        # 2. Reflection loop — too many reflections, suggesting LLM judge can't pass.
        if refl_visits >= REFLECTION_LOOP_THRESHOLD:
            report.issues.append(
                f"reflection_loop: {refl_visits} reflection cycles"
            )
            report.recommendations.append(
                "lower MultiGrader threshold or check for hard-rule veto causing repeated revisions"
            )

        # 3. Tool redundancy — one tool used disproportionately.
        for tool, n in tool_calls.items():
            if n >= TOOL_REDUNDANCY_THRESHOLD:
                report.issues.append(
                    f"tool_redundancy: '{tool}' called {n}× this conversation"
                )
                report.recommendations.append(
                    f"add result caching or stricter argument deduplication around '{tool}'"
                )

        # 4. Anomalies already raised by FlowMonitor.
        if anomaly_count:
            report.issues.append(f"{anomaly_count} flow anomaly/anomalies already raised")

        # Verdict.
        if not report.issues:
            report.verdict = "healthy"
        elif len(report.issues) <= 1:
            report.verdict = "noisy"
        else:
            report.verdict = "inefficient"

        return report


# --------------------------------------------------------------------------
# Singleton + API
# --------------------------------------------------------------------------
_analyzer: Optional[TraceAnalyzer] = None


def get_trace_analyzer() -> TraceAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = TraceAnalyzer()
    return _analyzer


# Pydantic model for FastAPI exposure.
class TraceReportModel(BaseModel):
    conversation_id: str
    verdict: str
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    stats: Dict[str, object] = Field(default_factory=dict)


router = APIRouter(prefix="/trace", tags=["governance"])


@router.get("/{conversation_id}", response_model=TraceReportModel)
async def get_trace_report(conversation_id: str) -> TraceReportModel:
    """Return an efficiency report for the given conversation."""
    report = get_trace_analyzer().analyze(conversation_id)
    if report.verdict == "unknown":
        raise HTTPException(status_code=404, detail="no flow data for conversation")
    return TraceReportModel(
        conversation_id=report.conversation_id,
        verdict=report.verdict,
        issues=report.issues,
        recommendations=report.recommendations,
        stats=report.stats,
    )
