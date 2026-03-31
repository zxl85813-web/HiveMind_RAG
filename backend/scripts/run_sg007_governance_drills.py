"""
Phase 5 / TASK-SG-007 governance drill runner.

Scenarios:
- steady: baseline stable traffic
- spike: burst traffic and rate-limit pressure
- chaos: dependency outage + breaker recovery + fallback activation

Outputs:
- JSON report: logs/service_governance/sg007_drill_report.json
- Markdown report: logs/service_governance/sg007_drill_report.md
"""

import argparse
import asyncio
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.core.logging import logger, setup_script_context, get_trace_logger
from app.services.claw_router_governance import ClawRouterGovernance
from app.services.dependency_circuit_breaker import DependencyCircuitBreakerManager, settings
from app.services.fallback_orchestrator import FallbackOrchestrator
from app.services.rate_limit_governance import RateLimitGovernanceCenter

# 初始化脚本上下文 (获取 trace_id, 标识模块)
setup_script_context("run_sg007_governance_drills")
t_logger = get_trace_logger("scripts.sg007_drills")

@dataclass
class ScenarioResult:
    name: str
    total_requests: int
    successful_requests: int
    blocked_requests: int
    degrade_triggers: int
    mttr_sec: float
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "blocked_requests": self.blocked_requests,
            "degrade_triggers": self.degrade_triggers,
            "degrade_trigger_ratio": ratio(self.degrade_triggers, self.total_requests),
            "error_budget_consumed": ratio(self.blocked_requests, self.total_requests),
            "mttr_sec": round(self.mttr_sec, 4),
            "notes": self.notes,
        }


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SG-007 governance drills and export reports")
    parser.add_argument(
        "--output-json",
        default="logs/service_governance/sg007_drill_report.json",
        help="Output JSON report path relative to backend/",
    )
    parser.add_argument(
        "--output-md",
        default="logs/service_governance/sg007_drill_report.md",
        help="Output Markdown report path relative to backend/",
    )
    parser.add_argument("--steady-requests", type=int, default=120)
    parser.add_argument("--steady-duration-sec", type=float, default=0.0)
    parser.add_argument("--steady-rps", type=float, default=2.0)
    parser.add_argument("--spike-requests", type=int, default=260)
    parser.add_argument("--chaos-requests", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--open-duration-sec", type=float, default=1.2)
    parser.add_argument("--max-error-budget", type=float, default=None)
    parser.add_argument("--max-degrade-trigger-ratio", type=float, default=None)
    parser.add_argument("--max-mttr-sec", type=float, default=None)
    parser.add_argument("--no-versioned", action="store_true")
    return parser


def _safe_token(value: str) -> str:
    out = "".join(ch for ch in value.lower() if ch.isalnum() or ch in {"-", "_"})
    return out or "na"


def _build_run_key() -> str:
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    sha = os.getenv("GITHUB_SHA", "local")[:8]
    run_id = os.getenv("GITHUB_RUN_ID", "local")
    return f"{_safe_token(ts)}_{_safe_token(sha)}_{_safe_token(run_id)}"


def _versioned_path(base_path: Path, run_key: str) -> Path:
    return base_path.with_name(f"{base_path.stem}_{run_key}{base_path.suffix}")


async def run_steady(steady_requests: int, seed: int) -> ScenarioResult:
    random.seed(seed)
    t_logger.info("Starting Steady State Drill", action="scenario_start", meta={"requests": steady_requests})
    router = ClawRouterGovernance()
    limiter = RateLimitGovernanceCenter()
    limiter.update_policies(
        [
            {
                "route": "/api/v1/chat/completions",
                "route_rule": {"enabled": True, "capacity": max(steady_requests, 120), "refill_per_sec": 9999.0},
                "user_rule": {"enabled": True, "capacity": max(steady_requests, 120), "refill_per_sec": 9999.0},
                "key_rule": {"enabled": False, "capacity": 1, "refill_per_sec": 0.0},
            }
        ]
    )

    total = steady_requests
    success = 0
    blocked = 0

    for i in range(total):
        msg = "quick status update" if i % 7 else "urgent architecture benchmark analysis"
        decision = limiter.check(route="/api/v1/chat/completions", user_id="steady-user", api_key=None)
        if not bool(decision["allowed"]):
            blocked += 1
            continue
        await router.decide([{"role": "user", "content": msg}])
        success += 1

    snap = router.snapshot()
    stats = snap["stats"]
    degradations = int(stats["cost_guard_downgrades"])  # type: ignore[index]

    t_logger.info("Steady state drill completed", action="scenario_end", meta={"name": "steady", "success": success, "blocked": blocked})

    return ScenarioResult(
        name="steady",
        total_requests=total,
        successful_requests=success,
        blocked_requests=blocked,
        degrade_triggers=degradations,
        mttr_sec=0.0,
        notes=["Stable traffic baseline with minimal throttling."],
    )


async def run_steady_for_duration(steady_duration_sec: float, steady_rps: float, seed: int) -> ScenarioResult:
    random.seed(seed)
    router = ClawRouterGovernance()
    limiter = RateLimitGovernanceCenter()
    buffer = max(int(max(steady_rps, 1.0) * 120), 120)
    limiter.update_policies(
        [
            {
                "route": "/api/v1/chat/completions",
                "route_rule": {"enabled": True, "capacity": buffer, "refill_per_sec": 9999.0},
                "user_rule": {"enabled": True, "capacity": buffer, "refill_per_sec": 9999.0},
                "key_rule": {"enabled": False, "capacity": 1, "refill_per_sec": 0.0},
            }
        ]
    )

    interval_sec = 1.0 / max(steady_rps, 0.1)
    deadline = time.perf_counter() + max(steady_duration_sec, 0.1)
    total = 0
    success = 0
    blocked = 0
    i = 0

    while time.perf_counter() < deadline:
        msg = "quick status update" if i % 7 else "urgent architecture benchmark analysis"
        decision = limiter.check(route="/api/v1/chat/completions", user_id="steady-user", api_key=None)
        total += 1
        if not bool(decision["allowed"]):
            blocked += 1
        else:
            await router.decide([{"role": "user", "content": msg}])
            success += 1
        i += 1
        await asyncio.sleep(interval_sec)

    snap = router.snapshot()
    stats = snap["stats"]
    degradations = int(stats["cost_guard_downgrades"])  # type: ignore[index]

    return ScenarioResult(
        name="steady",
        total_requests=total,
        successful_requests=success,
        blocked_requests=blocked,
        degrade_triggers=degradations,
        mttr_sec=0.0,
        notes=[
            "Steady traffic baseline with time-driven execution.",
            f"duration_sec={round(steady_duration_sec, 2)}",
            f"rps={round(steady_rps, 3)}",
        ],
    )


async def run_spike(spike_requests: int, seed: int) -> ScenarioResult:
    random.seed(seed + 1)
    t_logger.info("Starting Spike Drill", action="scenario_start", meta={"requests": spike_requests})
    router = ClawRouterGovernance()
    limiter = RateLimitGovernanceCenter()
    limiter.update_policies(
        [
            {
                "route": "/api/v1/chat/completions",
                "route_rule": {"enabled": True, "capacity": 30, "refill_per_sec": 0.5},
                "user_rule": {"enabled": True, "capacity": 10, "refill_per_sec": 0.2},
                "key_rule": {"enabled": False, "capacity": 1, "refill_per_sec": 0.0},
            }
        ]
    )

    total = spike_requests
    success = 0
    blocked = 0

    for i in range(total):
        msg = "status update " * (1200 if i % 6 == 0 else 20)
        decision = limiter.check(route="/api/v1/chat/completions", user_id=f"u-{i % 3}", api_key=None)
        if not bool(decision["allowed"]):
            blocked += 1
            continue
        await router.decide([{"role": "user", "content": msg}])
        success += 1

    snap = router.snapshot()
    stats = snap["stats"]
    degradations = int(stats["cost_guard_downgrades"]) + blocked  # type: ignore[index]
    
    t_logger.info("Spike drill completed", action="scenario_end", meta={"name": "spike", "success": success, "blocked": blocked})

    return ScenarioResult(
        name="spike",
        total_requests=total,
        successful_requests=success,
        blocked_requests=blocked,
        degrade_triggers=degradations,
        mttr_sec=0.0,
        notes=["Burst load emphasizes route/user token bucket behavior."],
    )


async def run_chaos(chaos_requests: int, seed: int, open_duration_sec: float) -> ScenarioResult:
    random.seed(seed + 2)
    t_logger.warning("Starting Chaos Drill (Circuit Breaker Failure Injection)", action="scenario_start", meta={"requests": chaos_requests})

    settings.CB_ENABLED = True
    settings.CB_WINDOW_SIZE = 6
    settings.CB_MIN_REQUESTS = 1
    settings.CB_ERROR_RATE_THRESHOLD = 0.5
    settings.CB_OPEN_DURATION_SEC = int(max(open_duration_sec, 1.0))
    settings.CB_HALF_OPEN_PROBES = 1
    settings.CB_TIMEOUT_LLM_MS = 200

    breaker = DependencyCircuitBreakerManager()
    fallback = FallbackOrchestrator()

    total = chaos_requests
    success = 0
    blocked = 0
    degradation = 0

    start = time.perf_counter()

    async def always_fail() -> str:
        raise RuntimeError("simulated llm outage")

    async def success_probe() -> str:
        return "ok"

    # Force OPEN state.
    try:
        await breaker.execute("llm", always_fail)
    except Exception:
        pass

    for i in range(total):
        try:
            await breaker.execute("llm", success_probe)
            success += 1
        except Exception:
            blocked += 1
            degradation += 1
            if i % 5 == 0:
                # Trigger fallback chain periodically.
                async def local_fail() -> str:
                    raise RuntimeError("local model down")

                async def backup_ok() -> str:
                    return "backup-response"

                try:
                    await fallback.recover_text(
                        query="chaos drill",
                        local_invoke=local_fail,
                        backup_invoke=backup_ok,
                    )
                    success += 1
                    degradation += 1
                except Exception:
                    pass

        if i == 0:
            await asyncio.sleep(open_duration_sec + 0.1)

    mttr = time.perf_counter() - start
    fb_stats = fallback.snapshot()["stats"]
    degradation += int(fb_stats["backup_provider_success"])  # type: ignore[index]
    
    t_logger.warning("Chaos drill completed", action="scenario_end", meta={"name": "chaos", "mttr": mttr, "degradations": degradation})

    return ScenarioResult(
        name="chaos",
        total_requests=total,
        successful_requests=success,
        blocked_requests=blocked,
        degrade_triggers=degradation,
        mttr_sec=mttr,
        notes=["Injected dependency failures to verify breaker + fallback convergence."],
    )


def build_summary(results: list[ScenarioResult]) -> dict[str, Any]:
    total_requests = sum(r.total_requests for r in results)
    total_blocked = sum(r.blocked_requests for r in results)
    total_degrade = sum(r.degrade_triggers for r in results)
    mttr_values = [r.mttr_sec for r in results if r.mttr_sec > 0]
    avg_mttr = round(sum(mttr_values) / len(mttr_values), 4) if mttr_values else 0.0

    return {
        "generated_at_epoch": int(time.time()),
        "scenarios": [r.to_dict() for r in results],
        "global": {
            "total_requests": total_requests,
            "total_blocked": total_blocked,
            "error_budget_consumed": ratio(total_blocked, total_requests),
            "degrade_trigger_ratio": ratio(total_degrade, total_requests),
            "avg_mttr_sec": avg_mttr,
        },
        "gate_hints": {
            "GATE-SG-1_stability": "pass" if ratio(total_blocked, total_requests) <= 0.2 else "risk",
            "GATE-SG-2_resilience": "pass" if avg_mttr <= 60.0 else "risk",
            "GATE-SG-3_cost": "pass" if ratio(total_degrade, total_requests) <= 0.5 else "observe",
            "GATE-SG-4_ops": "pass",
        },
    }


def add_run_metadata(summary: dict[str, Any], *, started_at_epoch: int, ended_at_epoch: int, run_key: str) -> None:
    duration_sec = max(0, ended_at_epoch - started_at_epoch)
    summary["run"] = {
        "started_at_epoch": started_at_epoch,
        "ended_at_epoch": ended_at_epoch,
        "duration_sec": duration_sec,
        "run_key": run_key,
    }


def evaluate_gate(
    summary: dict[str, Any],
    *,
    max_error_budget: float | None,
    max_degrade_trigger_ratio: float | None,
    max_mttr_sec: float | None,
) -> dict[str, Any]:
    global_stats = summary["global"]
    violations: list[dict[str, Any]] = []

    if max_error_budget is not None and global_stats["error_budget_consumed"] > max_error_budget:
        violations.append(
            {
                "metric": "error_budget_consumed",
                "actual": global_stats["error_budget_consumed"],
                "threshold": max_error_budget,
            }
        )

    if max_degrade_trigger_ratio is not None and global_stats["degrade_trigger_ratio"] > max_degrade_trigger_ratio:
        violations.append(
            {
                "metric": "degrade_trigger_ratio",
                "actual": global_stats["degrade_trigger_ratio"],
                "threshold": max_degrade_trigger_ratio,
            }
        )

    if max_mttr_sec is not None and global_stats["avg_mttr_sec"] > max_mttr_sec:
        violations.append(
            {
                "metric": "avg_mttr_sec",
                "actual": global_stats["avg_mttr_sec"],
                "threshold": max_mttr_sec,
            }
        )

    return {
        "enabled": any(v is not None for v in [max_error_budget, max_degrade_trigger_ratio, max_mttr_sec]),
        "passed": len(violations) == 0,
        "thresholds": {
            "max_error_budget": max_error_budget,
            "max_degrade_trigger_ratio": max_degrade_trigger_ratio,
            "max_mttr_sec": max_mttr_sec,
        },
        "violations": violations,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# SG-007 Drill Report")
    lines.append("")
    lines.append(f"- generated_at_epoch: {summary['generated_at_epoch']}")
    global_stats = summary["global"]
    lines.append(f"- total_requests: {global_stats['total_requests']}")
    lines.append(f"- error_budget_consumed: {global_stats['error_budget_consumed']}")
    lines.append(f"- degrade_trigger_ratio: {global_stats['degrade_trigger_ratio']}")
    lines.append(f"- avg_mttr_sec: {global_stats['avg_mttr_sec']}")
    lines.append("")
    lines.append("## Scenario Table")
    lines.append("")
    lines.append("| scenario | requests | blocked | success | degrade_triggers | error_budget | degrade_ratio | mttr_sec |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")

    for scenario in summary["scenarios"]:
        lines.append(
            "| {name} | {total_requests} | {blocked_requests} | {successful_requests} | "
            "{degrade_triggers} | {error_budget_consumed} | {degrade_trigger_ratio} | {mttr_sec} |".format(**scenario)
        )

    lines.append("")
    lines.append("## Gate Hints")
    lines.append("")
    for key, value in summary["gate_hints"].items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Notes")
    lines.append("- Steady/Spike/Chaos are synthetic drills for governance trend tracking.")
    lines.append("- For weekly evidence, archive this report under backend/logs/service_governance/.")

    gate_enforcement = summary.get("gate_enforcement")
    if isinstance(gate_enforcement, dict) and gate_enforcement.get("enabled"):
        lines.append("")
        lines.append("## Gate Enforcement")
        lines.append("")
        lines.append(f"- passed: {gate_enforcement.get('passed')}")
        thresholds = gate_enforcement.get("thresholds", {})
        lines.append(f"- max_error_budget: {thresholds.get('max_error_budget')}")
        lines.append(f"- max_degrade_trigger_ratio: {thresholds.get('max_degrade_trigger_ratio')}")
        lines.append(f"- max_mttr_sec: {thresholds.get('max_mttr_sec')}")

        violations = gate_enforcement.get("violations", [])
        if violations:
            lines.append("")
            lines.append("### Violations")
            for item in violations:
                lines.append(
                    f"- {item['metric']}: actual={item['actual']} threshold={item['threshold']}"
                )
    return "\n".join(lines)


async def main() -> None:
    args = _build_parser().parse_args()

    started_at_epoch = int(time.time())
    run_key = _build_run_key()

    if args.steady_duration_sec > 0:
        steady = await run_steady_for_duration(args.steady_duration_sec, args.steady_rps, args.seed)
    else:
        steady = await run_steady(args.steady_requests, args.seed)
    spike = await run_spike(args.spike_requests, args.seed)
    chaos = await run_chaos(args.chaos_requests, args.seed, args.open_duration_sec)

    summary = build_summary([steady, spike, chaos])
    ended_at_epoch = int(time.time())
    add_run_metadata(summary, started_at_epoch=started_at_epoch, ended_at_epoch=ended_at_epoch, run_key=run_key)
    gate_enforcement = evaluate_gate(
        summary,
        max_error_budget=args.max_error_budget,
        max_degrade_trigger_ratio=args.max_degrade_trigger_ratio,
        max_mttr_sec=args.max_mttr_sec,
    )
    summary["gate_enforcement"] = gate_enforcement

    output_json = backend_dir / args.output_json
    output_md = backend_dir / args.output_md
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(summary), encoding="utf-8")

    t_logger.info(f"[SG-007] json report: {output_json}", action="export", meta={"format": "json", "path": str(output_json)})
    t_logger.info(f"[SG-007] markdown report: {output_md}", action="export", meta={"format": "markdown", "path": str(output_md)})

    if not args.no_versioned:
        output_json_v = _versioned_path(output_json, run_key)
        output_md_v = _versioned_path(output_md, run_key)
        output_json_v.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md_v.write_text(render_markdown(summary), encoding="utf-8")
        t_logger.success(f"[SG-007] versioned json report: {output_json_v}")

    if gate_enforcement["enabled"] and not gate_enforcement["passed"]:
        t_logger.error(f"[SG-007] gate enforcement failed: {gate_enforcement['violations']}", action="gate_failure")
        raise SystemExit(2)
    
    t_logger.success("[SG-007] Drill completed successfully", action="completed")


if __name__ == "__main__":
    asyncio.run(main())
