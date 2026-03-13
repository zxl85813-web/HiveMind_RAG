"""
Phase 5 / Step-7 unified gate validator.

Consumes evidence artifacts from SG-003 and SG-007 and generates
an actionable Step-7 go/no-go report.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Phase 5 Step-7 governance gates")
    parser.add_argument("--sg007-json", default="logs/service_governance/sg007_drill_report.json")
    parser.add_argument("--step3-json", default="logs/service_governance/step3_cb_report.json")
    parser.add_argument("--sg3-json", default="logs/service_governance/step5_sg3_cost_quality_report.json")
    parser.add_argument("--sg1-json", default="logs/service_governance/gate_sg1_window_report.json")
    parser.add_argument("--output-json", default="logs/service_governance/step7_gate_report.json")
    parser.add_argument("--output-md", default="logs/service_governance/step7_gate_report.md")
    parser.add_argument("--max-error-budget", type=float, default=0.20)
    parser.add_argument("--max-steady-block-ratio", type=float, default=0.05)
    parser.add_argument("--min-run-duration-sec", type=int, default=0)
    parser.add_argument("--max-mttr-sec", type=float, default=60.0)
    parser.add_argument("--max-convergence-ms", type=float, default=60000.0)
    parser.add_argument("--max-degrade-trigger-ratio", type=float, default=0.50)
    parser.add_argument(
        "--required-ops-files",
        nargs="*",
        default=[
            "docs/guides/service_governance_drill_template.md",
            "docs/architecture/service_governance_topology.md",
        ],
    )
    parser.add_argument("--enforce", action="store_true", help="Exit with code 2 if any gate fails")
    return parser


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _find_scenario(summary: dict[str, Any], scenario_name: str) -> dict[str, Any] | None:
    for item in summary.get("scenarios", []):
        if item.get("name") == scenario_name:
            return item
    return None


def _to_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate_step7(
    sg007: dict[str, Any],
    step3: dict[str, Any],
    sg3: dict[str, Any] | None,
    sg1: dict[str, Any] | None,
    *,
    max_error_budget: float,
    max_steady_block_ratio: float,
    min_run_duration_sec: int,
    max_mttr_sec: float,
    max_convergence_ms: float,
    max_degrade_trigger_ratio: float,
    required_ops_files: list[str],
) -> dict[str, Any]:
    global_stats = sg007.get("global", {})
    run_meta = sg007.get("run", {})
    steady = _find_scenario(sg007, "steady") or {}

    run_duration = int(run_meta.get("duration_sec", 0) or 0)
    error_budget = _to_float(global_stats.get("error_budget_consumed"), 1.0)
    steady_error_budget = _to_float(steady.get("error_budget_consumed"), 1.0)
    steady_block_ratio = steady_error_budget

    gate1_base_pass = (
        steady_error_budget <= max_error_budget
        and steady_block_ratio <= max_steady_block_ratio
        and run_duration >= min_run_duration_sec
    )
    sg1_gate_pass = None
    sg1_metrics: dict[str, Any] | None = None
    if isinstance(sg1, dict):
        sg1_gate_pass = bool((sg1.get("gate_result") or {}).get("passed", False))
        raw_metrics = sg1.get("metrics")
        sg1_metrics = raw_metrics if isinstance(raw_metrics, dict) else None

    gate1_pass = gate1_base_pass and (sg1_gate_pass is not False)

    dep_results = step3.get("results", [])
    convergence_values = [float(item.get("convergence_ms", 10**9)) for item in dep_results]
    max_convergence_observed = max(convergence_values) if convergence_values else float("inf")
    mttr = _to_float(global_stats.get("avg_mttr_sec"), float(10**9))

    gate2_pass = (
        bool(step3.get("overall_success", False))
        and mttr <= max_mttr_sec
        and max_convergence_observed <= max_convergence_ms
    )

    degrade_ratio = _to_float(global_stats.get("degrade_trigger_ratio"), 1.0)
    sg3_gate_pass = None
    sg3_cost_reduction = None
    sg3_quality_delta = None
    sg3_thresholds: dict[str, Any] | None = None
    if isinstance(sg3, dict):
        gate_result = sg3.get("gate_result", {})
        metrics = sg3.get("metrics", {})
        sg3_gate_pass = bool(gate_result.get("passed", False))
        sg3_cost_reduction = metrics.get("cost_reduction_ratio")
        sg3_quality_delta = metrics.get("quality_delta")
        raw_thresholds = sg3.get("thresholds")
        sg3_thresholds = raw_thresholds if isinstance(raw_thresholds, dict) else None

    gate3_pass = (degrade_ratio <= max_degrade_trigger_ratio) and (sg3_gate_pass is not False)

    missing_ops_files = [p for p in required_ops_files if not (backend_dir.parent / p).exists()]
    gate4_pass = len(missing_ops_files) == 0

    gates = {
        "GATE-SG-1_stability": {
            "passed": gate1_pass,
            "actual": {
                "error_budget_consumed": error_budget,
                "steady_error_budget_consumed": steady_error_budget,
                "steady_block_ratio": steady_block_ratio,
                "run_duration_sec": run_duration,
                "sg1_window_gate_passed": sg1_gate_pass,
                "sg1_window_metrics": sg1_metrics,
            },
            "thresholds": {
                "max_error_budget": max_error_budget,
                "max_steady_block_ratio": max_steady_block_ratio,
                "min_run_duration_sec": min_run_duration_sec,
            },
        },
        "GATE-SG-2_resilience": {
            "passed": gate2_pass,
            "actual": {
                "avg_mttr_sec": mttr,
                "max_convergence_ms": max_convergence_observed,
                "step3_overall_success": bool(step3.get("overall_success", False)),
            },
            "thresholds": {
                "max_mttr_sec": max_mttr_sec,
                "max_convergence_ms": max_convergence_ms,
            },
        },
        "GATE-SG-3_cost": {
            "passed": gate3_pass,
            "actual": {
                "degrade_trigger_ratio": degrade_ratio,
                "sg3_gate_passed": sg3_gate_pass,
                "sg3_cost_reduction_ratio": sg3_cost_reduction,
                "sg3_quality_delta": sg3_quality_delta,
            },
            "thresholds": {
                "max_degrade_trigger_ratio": max_degrade_trigger_ratio,
                "sg3_thresholds": sg3_thresholds,
            },
        },
        "GATE-SG-4_ops": {
            "passed": gate4_pass,
            "actual": {"missing_files": missing_ops_files},
            "thresholds": {"required_files": required_ops_files},
        },
    }

    failed = [name for name, data in gates.items() if not data["passed"]]
    return {
        "generated_at_epoch": int(time.time()),
        "overall_passed": len(failed) == 0,
        "failed_gates": failed,
        "gates": gates,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Step-7 Governance Gate Report")
    lines.append("")
    lines.append(f"- generated_at_epoch: {report['generated_at_epoch']}")
    lines.append(f"- overall_passed: {report['overall_passed']}")
    lines.append(f"- failed_gates: {', '.join(report['failed_gates']) if report['failed_gates'] else 'none'}")
    lines.append("")

    for gate_name, gate_data in report["gates"].items():
        lines.append(f"## {gate_name}")
        lines.append(f"- passed: {gate_data['passed']}")
        lines.append("- actual:")
        for key, value in gate_data["actual"].items():
            lines.append(f"  - {key}: {value}")
        lines.append("- thresholds:")
        for key, value in gate_data["thresholds"].items():
            lines.append(f"  - {key}: {value}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = _build_parser().parse_args()

    sg007_path = backend_dir / args.sg007_json
    step3_path = backend_dir / args.step3_json
    sg3_path = backend_dir / args.sg3_json
    sg1_path = backend_dir / args.sg1_json
    output_json = backend_dir / args.output_json
    output_md = backend_dir / args.output_md

    sg007 = _read_json(sg007_path)
    step3 = _read_json(step3_path)
    sg3 = _read_json_if_exists(sg3_path)
    sg1 = _read_json_if_exists(sg1_path)

    report = evaluate_step7(
        sg007,
        step3,
        sg3,
        sg1,
        max_error_budget=args.max_error_budget,
        max_steady_block_ratio=args.max_steady_block_ratio,
        min_run_duration_sec=args.min_run_duration_sec,
        max_mttr_sec=args.max_mttr_sec,
        max_convergence_ms=args.max_convergence_ms,
        max_degrade_trigger_ratio=args.max_degrade_trigger_ratio,
        required_ops_files=args.required_ops_files,
    )

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")

    print(f"[Step-7] json report: {output_json}")
    print(f"[Step-7] markdown report: {output_md}")

    if args.enforce and not report["overall_passed"]:
        print(f"[Step-7] failed gates: {report['failed_gates']}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
