"""
Phase 5 / Step-7 closure readiness validator.

Evaluates whether Step-7 can be formally closed based on recent
Gate evidence artifacts.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import time
import sys
from pathlib import Path
from typing import Any

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("validate_step7_closure_readiness")
t_logger = get_trace_logger("scripts.step7_readiness")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Step-7 closure readiness")
    parser.add_argument("--step7-json", default="logs/service_governance/step7_gate_report.json")
    parser.add_argument("--sg1-window-glob", default="logs/service_governance/gate_sg1_window_report_*.json")
    parser.add_argument("--sg1-min-pass-count", type=int, default=1)
    parser.add_argument("--sg1-window-hours", type=float, default=24.0)
    parser.add_argument("--output-json", default="logs/service_governance/step7_closure_readiness_report.json")
    parser.add_argument("--output-md", default="logs/service_governance/step7_closure_readiness_report.md")
    parser.add_argument("--no-versioned", action="store_true")
    parser.add_argument("--enforce", action="store_true")
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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_sg1_window_reports(args: argparse.Namespace) -> list[dict[str, Any]]:
    now_epoch = int(time.time())
    lower_bound = now_epoch - int(args.sg1_window_hours * 3600)
    paths = [Path(p) for p in glob.glob(str(backend_dir / args.sg1_window_glob))]
    paths.sort()

    reports: list[dict[str, Any]] = []
    for p in paths:
        try:
            payload = _read_json(p)
        except Exception:
            continue
        generated_at = int(payload.get("generated_at_epoch", 0) or 0)
        if generated_at < lower_bound:
            continue
        reports.append({"path": str(p), "payload": payload})
    return reports


def evaluate_readiness(args: argparse.Namespace) -> dict[str, Any]:
    step7_path = backend_dir / args.step7_json
    step7 = _read_json(step7_path)
    step7_passed = bool(step7.get("overall_passed", False))

    sg1_reports = _collect_sg1_window_reports(args)
    sg1_pass_count = sum(1 for r in sg1_reports if bool((r["payload"].get("gate_result") or {}).get("passed", False)))
    sg1_ready = sg1_pass_count >= args.sg1_min_pass_count

    gate_states = step7.get("gates", {})
    gate_details = {
        "sg1": bool((gate_states.get("GATE-SG-1_stability") or {}).get("passed", False)),
        "sg2": bool((gate_states.get("GATE-SG-2_resilience") or {}).get("passed", False)),
        "sg3": bool((gate_states.get("GATE-SG-3_cost") or {}).get("passed", False)),
        "sg4": bool((gate_states.get("GATE-SG-4_ops") or {}).get("passed", False)),
    }

    closure_ready = step7_passed and sg1_ready and all(gate_details.values())

    return {
        "generated_at_epoch": int(time.time()),
        "step7_report_path": str(step7_path),
        "step7_overall_passed": step7_passed,
        "gate_details": gate_details,
        "sg1_window": {
            "window_hours": args.sg1_window_hours,
            "min_pass_count": args.sg1_min_pass_count,
            "actual_pass_count": sg1_pass_count,
            "report_count": len(sg1_reports),
            "passed_report_paths": [r["path"] for r in sg1_reports if bool((r["payload"].get("gate_result") or {}).get("passed", False))],
        },
        "closure_ready": closure_ready,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Step-7 Closure Readiness Report")
    lines.append("")
    lines.append(f"- generated_at_epoch: {report['generated_at_epoch']}")
    lines.append(f"- step7_overall_passed: {report['step7_overall_passed']}")
    lines.append(f"- closure_ready: {report['closure_ready']}")
    lines.append("")

    lines.append("## Gate Details")
    lines.append("")
    for key, value in report["gate_details"].items():
        lines.append(f"- {key}: {value}")

    sg1_window = report["sg1_window"]
    lines.append("")
    lines.append("## SG1 Window Requirement")
    lines.append("")
    lines.append(f"- window_hours: {sg1_window['window_hours']}")
    lines.append(f"- min_pass_count: {sg1_window['min_pass_count']}")
    lines.append(f"- actual_pass_count: {sg1_window['actual_pass_count']}")
    lines.append(f"- report_count: {sg1_window['report_count']}")

    return "\n".join(lines)


def main() -> None:
    args = _build_parser().parse_args()
    run_key = _build_run_key()

    report = evaluate_readiness(args)
    report["run_key"] = run_key

    output_json = backend_dir / args.output_json
    output_md = backend_dir / args.output_md
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")

    t_logger.info(f"[Step-7-Ready] json report: {output_json}", action="export")
    t_logger.info(f"[Step-7-Ready] markdown report: {output_md}", action="export")

    if not args.no_versioned:
        output_json_v = _versioned_path(output_json, run_key)
        output_md_v = _versioned_path(output_md, run_key)
        output_json_v.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md_v.write_text(render_markdown(report), encoding="utf-8")
        t_logger.success(f"[Step-7-Ready] versioned json report: {output_json_v}")

    if args.enforce and not bool(report["closure_ready"]):
        t_logger.error("[Step-7-Ready] closure not ready", report_data=report, action="gate_failure")
        raise SystemExit(2)
    
    t_logger.success("[Step-7-Ready] System is ready for closure", action="gate_pass")


if __name__ == "__main__":
    main()
