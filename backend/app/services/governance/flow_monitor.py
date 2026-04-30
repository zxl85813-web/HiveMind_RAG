"""
Sensitivity / Flow Monitoring (Anthropic 2.1J).

What it watches
---------------
The model's *content* changes constantly; what stays stable in a healthy
agent is the **shape of its decision flow**: which nodes it visits,
how often it re-enters supervisor, how many times it calls the same
tool with the same args.

Anthropic's recommendation is to monitor *that* logical signal — not
the user content — so you can:

- catch a planning loop ("supervisor → reflection → supervisor → ...")
  before it burns budget,
- spot tool abuse ("`web_search` called 14 times this conversation"),
- identify ring-specific regressions ("canary cycle rate is 3× stable").

What it does NOT do
-------------------
- Inspect message contents (avoid PII / observability separation).
- Block traffic. It only emits warnings via loguru and returns
  structured anomaly objects callers can act on.

State is per-process and per-conversation, capped to ~1k conversations
(LRU). For multi-process deployments you'd persist this to a metrics
backend (Prometheus, OTel, ...) — left as a follow-up; the local
detector still surfaces in logs immediately.
"""

from __future__ import annotations

import threading
import time
from collections import Counter, OrderedDict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loguru import logger


# Tunables — sensible defaults; override per-process if the agent is
# legitimately bursty.
CYCLE_WINDOW = 6              # last N node visits checked for cycles
CYCLE_REPEAT_THRESHOLD = 3    # same node ≥3 times in CYCLE_WINDOW → cycle
TOOL_ABUSE_THRESHOLD = 10     # same tool called ≥10 times → abuse
DUPLICATE_ARGS_THRESHOLD = 4  # same (tool, args) ≥4 times → likely loop
MAX_CONVERSATIONS = 1000      # LRU cap for in-memory tracking


@dataclass
class FlowAnomaly:
    """A structured anomaly suitable for logging or metric emission."""

    kind: str              # "cycle" | "tool_abuse" | "duplicate_args" | "runaway"
    conversation_id: str
    detail: str
    severity: str = "warn"  # "warn" | "alert"


@dataclass
class _ConversationFlow:
    started_at: float = field(default_factory=time.time)
    visits: deque = field(default_factory=lambda: deque(maxlen=64))
    node_counter: Counter = field(default_factory=Counter)
    tool_counter: Counter = field(default_factory=Counter)
    tool_args_counter: Counter = field(default_factory=Counter)
    anomalies_seen: set = field(default_factory=set)


class FlowMonitor:
    """Per-conversation passive flow tracker."""

    def __init__(self, *, max_conversations: int = MAX_CONVERSATIONS):
        self._flows: "OrderedDict[str, _ConversationFlow]" = OrderedDict()
        self._lock = threading.Lock()
        self._max_conversations = max_conversations

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def _flow(self, conversation_id: str) -> _ConversationFlow:
        with self._lock:
            flow = self._flows.get(conversation_id)
            if flow is None:
                flow = _ConversationFlow()
                self._flows[conversation_id] = flow
                while len(self._flows) > self._max_conversations:
                    self._flows.popitem(last=False)
            else:
                self._flows.move_to_end(conversation_id)
            return flow

    def record_node(
        self, conversation_id: str, node: str
    ) -> List[FlowAnomaly]:
        """Record a node visit and return any newly-detected anomalies."""
        if not conversation_id or not node:
            return []
        flow = self._flow(conversation_id)
        flow.visits.append(node)
        flow.node_counter[node] += 1
        return self._detect_cycles(conversation_id, flow)

    def record_tool(
        self,
        conversation_id: str,
        tool_name: str,
        args: Optional[dict] = None,
    ) -> List[FlowAnomaly]:
        """Record a tool invocation and return any newly-detected anomalies."""
        if not conversation_id or not tool_name:
            return []
        flow = self._flow(conversation_id)
        flow.tool_counter[tool_name] += 1
        # Hash args by their repr — cheap and good enough to spot
        # identical-call loops; we don't need cryptographic accuracy.
        args_key = (tool_name, repr(sorted((args or {}).items()))[:200])
        flow.tool_args_counter[args_key] += 1
        return self._detect_tool_abuse(conversation_id, flow, tool_name, args_key)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def _detect_cycles(
        self, conversation_id: str, flow: _ConversationFlow
    ) -> List[FlowAnomaly]:
        anomalies: List[FlowAnomaly] = []
        window = list(flow.visits)[-CYCLE_WINDOW:]
        if len(window) >= CYCLE_WINDOW:
            counts = Counter(window)
            for node, n in counts.items():
                if n >= CYCLE_REPEAT_THRESHOLD:
                    key = ("cycle", node)
                    if key not in flow.anomalies_seen:
                        flow.anomalies_seen.add(key)
                        anomaly = FlowAnomaly(
                            kind="cycle",
                            conversation_id=conversation_id,
                            detail=(
                                f"node='{node}' visited {n}× in last "
                                f"{CYCLE_WINDOW} steps"
                            ),
                            severity="alert",
                        )
                        anomalies.append(anomaly)
                        logger.warning(
                            f"🔁 [FlowMonitor] CYCLE conv={conversation_id} {anomaly.detail}"
                        )
        # Runaway: too many total node visits.
        total = sum(flow.node_counter.values())
        if total >= 50 and ("runaway", "total") not in flow.anomalies_seen:
            flow.anomalies_seen.add(("runaway", "total"))
            anomaly = FlowAnomaly(
                kind="runaway",
                conversation_id=conversation_id,
                detail=f"{total} node visits in single conversation",
                severity="alert",
            )
            anomalies.append(anomaly)
            logger.warning(f"🔁 [FlowMonitor] RUNAWAY conv={conversation_id} {anomaly.detail}")
        return anomalies

    def _detect_tool_abuse(
        self,
        conversation_id: str,
        flow: _ConversationFlow,
        tool_name: str,
        args_key,
    ) -> List[FlowAnomaly]:
        anomalies: List[FlowAnomaly] = []
        if flow.tool_counter[tool_name] >= TOOL_ABUSE_THRESHOLD:
            key = ("tool_abuse", tool_name)
            if key not in flow.anomalies_seen:
                flow.anomalies_seen.add(key)
                anomaly = FlowAnomaly(
                    kind="tool_abuse",
                    conversation_id=conversation_id,
                    detail=(
                        f"tool='{tool_name}' invoked "
                        f"{flow.tool_counter[tool_name]}× this conversation"
                    ),
                    severity="warn",
                )
                anomalies.append(anomaly)
                logger.warning(
                    f"🛠️ [FlowMonitor] TOOL_ABUSE conv={conversation_id} {anomaly.detail}"
                )
        if flow.tool_args_counter[args_key] >= DUPLICATE_ARGS_THRESHOLD:
            key = ("dup_args", tool_name, args_key[1])
            if key not in flow.anomalies_seen:
                flow.anomalies_seen.add(key)
                anomaly = FlowAnomaly(
                    kind="duplicate_args",
                    conversation_id=conversation_id,
                    detail=(
                        f"tool='{tool_name}' called with identical args "
                        f"{flow.tool_args_counter[args_key]}× — likely loop"
                    ),
                    severity="alert",
                )
                anomalies.append(anomaly)
                logger.warning(
                    f"🔂 [FlowMonitor] DUP_ARGS conv={conversation_id} {anomaly.detail}"
                )
        return anomalies

    # ------------------------------------------------------------------
    # Inspection / cleanup
    # ------------------------------------------------------------------
    def snapshot(self, conversation_id: str) -> Dict[str, object]:
        flow = self._flows.get(conversation_id)
        if flow is None:
            return {}
        return {
            "started_at": flow.started_at,
            "node_visits": dict(flow.node_counter),
            "tool_calls": dict(flow.tool_counter),
            "anomaly_count": len(flow.anomalies_seen),
        }

    def reset(self, conversation_id: Optional[str] = None) -> None:
        with self._lock:
            if conversation_id is None:
                self._flows.clear()
            else:
                self._flows.pop(conversation_id, None)


# --------------------------------------------------------------------------
# Singleton — keyed by tenant so cross-tenant traffic doesn't share state.
# --------------------------------------------------------------------------
_monitors: dict[str, "FlowMonitor"] = {}
_lock = threading.Lock()


def get_flow_monitor(tenant_id: Optional[str] = None) -> FlowMonitor:
    if tenant_id is None:
        try:
            from app.core.tenant_context import get_current_tenant

            tenant_id = get_current_tenant()
        except Exception:  # noqa: BLE001
            tenant_id = "default"
    key = tenant_id or "default"
    mon = _monitors.get(key)
    if mon is None:
        with _lock:
            mon = _monitors.get(key)
            if mon is None:
                mon = FlowMonitor()
                _monitors[key] = mon
    return mon
