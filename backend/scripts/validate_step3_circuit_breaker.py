"""
Manual validation script for Phase 5 / TASK-SG-003 circuit breaker behavior.

Scenarios:
1) LLM failure -> OPEN
2) OPEN blocks immediate retry
3) OPEN duration elapsed -> HALF_OPEN probe
4) Probe success -> CLOSED
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Literal, cast

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("validate_step3_circuit_breaker")
t_logger = get_trace_logger("scripts.cb_validator")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.services.dependency_circuit_breaker import DependencyCircuitBreakerManager, settings  # noqa: E402

DependencyName = Literal["llm", "es", "neo4j"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate dependency circuit-breaker convergence and export reports")
    parser.add_argument(
        "--deps",
        nargs="+",
        default=["llm", "es", "neo4j"],
        help="Dependencies to test, e.g. --deps llm es neo4j",
    )
    parser.add_argument(
        "--open-duration-sec",
        type=float,
        default=2.0,
        help="OPEN duration used by this validation run",
    )
    parser.add_argument(
        "--output-json",
        default="logs/service_governance/step3_cb_report.json",
        help="Output JSON report path (relative to backend/)",
    )
    parser.add_argument(
        "--output-md",
        default="logs/service_governance/step3_cb_report.md",
        help="Output Markdown report path (relative to backend/)",
    )
    parser.add_argument(
        "--no-versioned",
        action="store_true",
        help="Disable writing versioned report copies (timestamp + sha + run id)",
    )
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


async def _run_one_dependency(dep: DependencyName, open_duration_sec: float) -> dict[str, Any]:
    # Speed up local validation.
    settings.CB_ENABLED = True
    settings.CB_WINDOW_SIZE = 5
    settings.CB_MIN_REQUESTS = 1
    settings.CB_ERROR_RATE_THRESHOLD = 0.5
    settings.CB_OPEN_DURATION_SEC = int(max(open_duration_sec, 1))
    settings.CB_HALF_OPEN_PROBES = 1
    settings.CB_TIMEOUT_LLM_MS = 200
    settings.CB_TIMEOUT_ES_MS = 200
    settings.CB_TIMEOUT_NEO4J_MS = 200

    cb = DependencyCircuitBreakerManager()

    started_at = time.perf_counter()

    t_logger.info(f"[Step3-Validate] [{dep}] Scenario 1: trigger OPEN")

    async def fail_once():
        raise RuntimeError(f"simulated {dep} outage")

    open_triggered = False
    open_blocked = False
    closed_after_probe = False
    errors: list[str] = []

    try:
        await cb.execute(dep, fail_once)
    except Exception as exc:
        t_logger.info(f"expected failure: {exc}")

    snapshot_open = cast(dict[str, Any], cb.snapshot().get(dep, {}))
    open_triggered = snapshot_open.get("state") == "OPEN"

    t_logger.info(f"[Step3-Validate] [{dep}] snapshot-open: {{}}", snapshot_open)

    t_logger.info(f"[Step3-Validate] [{dep}] Scenario 2: OPEN should block immediately")
    try:
        await cb.execute(dep, lambda: asyncio.sleep(0))
    except Exception as exc:
        msg = str(exc)
        t_logger.info(f"expected open-block: {msg}")
        open_blocked = f"Dependency circuit OPEN: {dep}" in msg

    t_logger.info(f"[Step3-Validate] [{dep}] waiting for open duration...")
    await asyncio.sleep(open_duration_sec + 0.2)

    t_logger.info(f"[Step3-Validate] [{dep}] Scenario 3/4: half-open probe success closes circuit")

    async def success_probe():
        return "ok"

    try:
        probe_result = await cb.execute(dep, success_probe)
        t_logger.info("probe result: {}", probe_result)
    except Exception as exc:
        errors.append(f"probe failed: {exc}")

    snapshot_closed = cast(dict[str, Any], cb.snapshot().get(dep, {}))
    closed_after_probe = snapshot_closed.get("state") == "CLOSED"

    convergence_ms = round(cast(float, time.perf_counter() - started_at) * 1000, 2)

    success = open_triggered and open_blocked and closed_after_probe and not errors
    if not success:
        if not open_triggered:
            errors.append("OPEN not triggered")
        if not open_blocked:
            errors.append("OPEN did not block immediate retry")
        if not closed_after_probe:
            errors.append("HALF_OPEN probe did not close circuit")

    t_logger.info(f"[{dep}] snapshot-closed: {{}}", snapshot_closed, action="cb_check")

    return {
        "dependency": dep,
        "success": success,
        "convergence_ms": convergence_ms,
        "open_triggered": open_triggered,
        "open_blocked": open_blocked,
        "closed_after_probe": closed_after_probe,
        "snapshot_open": snapshot_open,
        "snapshot_closed": snapshot_closed,
        "errors": errors,
    }


def _render_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Step-3 Circuit Breaker Validation Report")
    lines.append("")
    lines.append(f"- overall_success: {summary['overall_success']}")
    tested_dependencies = cast(list[str], summary["tested_dependencies"])
    lines.append(f"- tested_dependencies: {', '.join(tested_dependencies)}")
    lines.append(f"- generated_at: {summary['generated_at_epoch']}")
    lines.append("")
    lines.append("| dependency | success | convergence_ms | open_triggered | open_blocked | closed_after_probe |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    results = cast(list[dict[str, Any]], summary["results"])
    for r in results:
        lines.append(
            f"| {r['dependency']} | {r['success']} | {r['convergence_ms']} | {r['open_triggered']} | {r['open_blocked']} | {r['closed_after_probe']} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("- Scenario: failure -> OPEN -> immediate block -> wait -> HALF_OPEN probe -> CLOSED")
    lines.append("- This is a local fault-injection validation, intended as GATE-SG-2 evidence artifact.")
    return "\n".join(lines)


async def main() -> None:
    args = _build_parser().parse_args()
    deps_raw = [d.strip().lower() for d in args.deps if d.strip()]
    invalid = [d for d in deps_raw if d not in {"llm", "es", "neo4j"}]
    if invalid:
        t_logger.error(f"Unsupported dependencies: {invalid}")
        raise ValueError(f"Unsupported dependencies: {invalid}")

    deps = cast(list[DependencyName], deps_raw)

    t_logger.info(f"Starting CB validation for deps: {deps}", action="batch_check_start")

    results: list[dict[str, Any]] = []
    for dep in deps:
        t_logger.info(f"Checking dependency: {dep}", action="cb_check_start", meta={"dependency": dep})
        results.append(await _run_one_dependency(dep, args.open_duration_sec))

    overall_success = all(bool(r["success"]) for r in results)
    summary = {
        "overall_success": overall_success,
        "tested_dependencies": deps,
        "generated_at_epoch": int(time.time()),
        "run_key": _build_run_key(),
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "results": results,
    }

    out_json = backend_dir / args.output_json
    out_md = backend_dir / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_render_markdown(summary), encoding="utf-8")

    t_logger.info(f"json report: {out_json}", action="export")
    t_logger.info(f"markdown report: {out_md}", action="export")

    if not args.no_versioned:
        run_key = cast(str, summary["run_key"])
        out_json_v = _versioned_path(out_json, run_key)
        out_md_v = _versioned_path(out_md, run_key)
        out_json_v.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        out_md_v.write_text(_render_markdown(summary), encoding="utf-8")
        t_logger.success(f"versioned json report: {out_json_v}")

    if overall_success:
        t_logger.success("[Step3-Validate] completed", action="gate_pass")
        return

    t_logger.error("[Step3-Validate] completed with failures", action="gate_failure")
    raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
