import argparse
import json
import time
from pathlib import Path

from scripts.validate_gate_sg1_stability_window import evaluate_window


def _write_report(path: Path, *, generated_at: int, total_requests: int, total_blocked: int, steady_blocked: int) -> None:
    payload = {
        "generated_at_epoch": generated_at,
        "global": {
            "total_requests": total_requests,
            "total_blocked": total_blocked,
        },
        "scenarios": [
            {
                "name": "steady",
                "total_requests": total_requests // 2,
                "blocked_requests": steady_blocked,
            }
        ],
        "gate_hints": {"GATE-SG-1_stability": "pass"},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _args(glob_pattern: str, **overrides):
    base = {
        "reports_glob": glob_pattern,
        "window_hours": 24.0,
        "min_reports": 1,
        "max_global_error_budget": 0.2,
        "max_steady_block_ratio": 0.1,
        "require_sg1_hint_pass": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_window_gate_passes_with_recent_reports(tmp_path: Path):
    now = int(time.time())
    report_path = tmp_path / "sg007_drill_report_1.json"
    _write_report(report_path, generated_at=now, total_requests=100, total_blocked=10, steady_blocked=3)

    pattern = str(report_path).replace("sg007_drill_report_1.json", "sg007_drill_report_*.json")
    report = evaluate_window(_args(pattern))

    assert report["gate_result"]["passed"] is True
    assert report["report_count"] >= 1


def test_window_gate_fails_when_not_enough_reports(tmp_path: Path):
    now = int(time.time())
    report_path = tmp_path / "sg007_drill_report_1.json"
    _write_report(report_path, generated_at=now, total_requests=100, total_blocked=5, steady_blocked=1)

    pattern = str(report_path).replace("sg007_drill_report_1.json", "sg007_drill_report_*.json")
    report = evaluate_window(_args(pattern, min_reports=3))

    assert report["gate_result"]["passed"] is False
    assert report["gate_result"]["enough_reports"] is False
