"""
Phase 5 / GATE-SG-1 stability window validator.

Aggregates SG-007 drill reports in a rolling time window (default 24h)
and generates formal stability evidence.
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
setup_script_context("validate_gate_sg1_stability_window")
t_logger = get_trace_logger("scripts.gate_sg1_validator")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate GATE-SG-1 over rolling SG-007 evidence window")
    parser.add_argument("--reports-glob", default="logs/service_governance/sg007_drill_report_*.json")
    parser.add_argument("--window-hours", type=float, default=24.0)
    parser.add_argument("--min-reports", type=int, default=1)
    parser.add_argument("--max-global-error-budget", type=float, default=0.20)
    parser.add_argument("--max-steady-block-ratio", type=float, default=0.05)
    parser.add_argument("--require-sg1-hint-pass", action="store_true")
    parser.add_argument("--output-json", default="logs/service_governance/gate_sg1_window_report.json")
    parser.add_argument("--output-md", default="logs/service_governance/gate_sg1_window_report.md")
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


def _pick_reports(args: argparse.Namespace) -> list[dict[str, Any]]:
    now_epoch = int(time.time())
    lower_bound = now_epoch - int(args.window_hours * 3600)
    report_paths = [Path(p) for p in glob.glob(str(backend_dir / args.reports_glob))]
    report_paths.sort()

    selected: list[dict[str, Any]] = []
    for path in report_paths:
        try:
            payload = _read_json(path)
        except Exception:
            continue

        generated_at = int(payload.get("generated_at_epoch", 0) or 0)
        if generated_at < lower_bound:
            continue

        selected.append({"path": str(path), "report": payload})

    return selected


def evaluate_window(args: argparse.Namespace) -> dict[str, Any]:
    picked = _pick_reports(args)

    global_total_requests = 0
    global_total_blocked = 0
    steady_total_requests = 0
    steady_total_blocked = 0
    sg1_hint_non_pass = 0

    for item in picked:
        report = item["report"]
        global_data = report.get("global", {})
        global_total_requests += int(global_data.get("total_requests", 0) or 0)
        global_total_blocked += int(global_data.get("total_blocked", 0) or 0)

        for scenario in report.get("scenarios", []):
            if scenario.get("name") != "steady":
                continue
            steady_total_requests += int(scenario.get("total_requests", 0) or 0)
            steady_total_blocked += int(scenario.get("blocked_requests", 0) or 0)

        gate_hints = report.get("gate_hints", {})
        if str(gate_hints.get("GATE-SG-1_stability", "")).lower() != "pass":
            sg1_hint_non_pass += 1

    global_error_budget = (global_total_blocked / global_total_requests) if global_total_requests > 0 else 1.0
    steady_block_ratio = (steady_total_blocked / steady_total_requests) if steady_total_requests > 0 else 1.0

    enough_reports = len(picked) >= args.min_reports
    global_budget_ok = global_error_budget <= args.max_global_error_budget
    steady_ok = steady_block_ratio <= args.max_steady_block_ratio
    hint_ok = (not args.require_sg1_hint_pass) or (sg1_hint_non_pass == 0)

    passed = enough_reports and global_budget_ok and steady_ok and hint_ok

    return {
        "generated_at_epoch": int(time.time()),
        "window_hours": args.window_hours,
        "report_count": len(picked),
        "report_paths": [item["path"] for item in picked],
        "metrics": {
            "global_total_requests": global_total_requests,
            "global_total_blocked": global_total_blocked,
            "global_error_budget": round(global_error_budget, 6),
            "steady_total_requests": steady_total_requests,
            "steady_total_blocked": steady_total_blocked,
            "steady_block_ratio": round(steady_block_ratio, 6),
            "sg1_hint_non_pass_reports": sg1_hint_non_pass,
        },
        "thresholds": {
            "min_reports": args.min_reports,
            "max_global_error_budget": args.max_global_error_budget,
            "max_steady_block_ratio": args.max_steady_block_ratio,
            "require_sg1_hint_pass": args.require_sg1_hint_pass,
        },
        "gate_result": {
            "passed": passed,
            "enough_reports": enough_reports,
            "global_budget_ok": global_budget_ok,
            "steady_ok": steady_ok,
            "hint_ok": hint_ok,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    m = report["metrics"]
    t = report["thresholds"]
    g = report["gate_result"]

    lines: list[str] = []
    lines.append("# GATE-SG-1 Stability Window Report")
    lines.append("")
    lines.append(f"- generated_at_epoch: {report['generated_at_epoch']}")
    lines.append(f"- window_hours: {report['window_hours']}")
    lines.append(f"- report_count: {report['report_count']}")
    lines.append(f"- gate_passed: {g['passed']}")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- global_total_requests: {m['global_total_requests']}")
    lines.append(f"- global_total_blocked: {m['global_total_blocked']}")
    lines.append(f"- global_error_budget: {m['global_error_budget']}")
    lines.append(f"- steady_total_requests: {m['steady_total_requests']}")
    lines.append(f"- steady_total_blocked: {m['steady_total_blocked']}")
    lines.append(f"- steady_block_ratio: {m['steady_block_ratio']}")
    lines.append(f"- sg1_hint_non_pass_reports: {m['sg1_hint_non_pass_reports']}")
    lines.append("")
    lines.append("## Thresholds")
    lines.append("")
    lines.append(f"- min_reports: {t['min_reports']}")
    lines.append(f"- max_global_error_budget: {t['max_global_error_budget']}")
    lines.append(f"- max_steady_block_ratio: {t['max_steady_block_ratio']}")
    lines.append(f"- require_sg1_hint_pass: {t['require_sg1_hint_pass']}")
    lines.append("")
    lines.append("## Gate Evaluation")
    lines.append("")
    lines.append(f"- enough_reports: {g['enough_reports']}")
    lines.append(f"- global_budget_ok: {g['global_budget_ok']}")
    lines.append(f"- steady_ok: {g['steady_ok']}")
    lines.append(f"- hint_ok: {g['hint_ok']}")
    return "\n".join(lines)


def main() -> None:
    args = _build_parser().parse_args()
    run_key = _build_run_key()

    report = evaluate_window(args)
    report["run_key"] = run_key

    output_json = backend_dir / args.output_json
    output_md = backend_dir / args.output_md
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")

    t_logger.info(f"[GATE-SG-1] json report: {output_json}", action="export")
    t_logger.info(f"[GATE-SG-1] markdown report: {output_md}", action="export")

    if not args.no_versioned:
        output_json_v = _versioned_path(output_json, run_key)
        output_md_v = _versioned_path(output_md, run_key)
        output_json_v.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md_v.write_text(render_markdown(report), encoding="utf-8")
        t_logger.success(f"[GATE-SG-1] versioned json report: {output_json_v}")

    if args.enforce and not bool(report["gate_result"]["passed"]):
        t_logger.error(f"[GATE-SG-1] gate failed: {report['gate_result']}", action="gate_failure")
        raise SystemExit(2)
    
    t_logger.success("[GATE-SG-1] Stability validation passed", action="gate_pass")


if __name__ == "__main__":
    main()
