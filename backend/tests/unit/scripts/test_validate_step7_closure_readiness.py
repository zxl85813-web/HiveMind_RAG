from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_step7_closure_readiness as mod


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_readiness_passes_with_step7_and_sg1_windows(tmp_path, monkeypatch):
    backend_root = tmp_path
    monkeypatch.setattr(mod, "backend_dir", backend_root)

    _write_json(
        backend_root / "logs/service_governance/step7_gate_report.json",
        {
            "overall_passed": True,
            "gates": {
                "GATE-SG-1_stability": {"passed": True},
                "GATE-SG-2_resilience": {"passed": True},
                "GATE-SG-3_cost": {"passed": True},
                "GATE-SG-4_ops": {"passed": True},
            },
        },
    )

    _write_json(
        backend_root / "logs/service_governance/gate_sg1_window_report_20260313-000000_x.json",
        {
            "generated_at_epoch": 9999999999,
            "gate_result": {"passed": True},
        },
    )

    args = mod._build_parser().parse_args(
        [
            "--sg1-min-pass-count",
            "1",
            "--sg1-window-hours",
            "24",
        ]
    )

    report = mod.evaluate_readiness(args)
    assert report["step7_overall_passed"] is True
    assert report["sg1_window"]["actual_pass_count"] == 1
    assert report["closure_ready"] is True


def test_readiness_fails_when_insufficient_sg1_passes(tmp_path, monkeypatch):
    backend_root = tmp_path
    monkeypatch.setattr(mod, "backend_dir", backend_root)

    _write_json(
        backend_root / "logs/service_governance/step7_gate_report.json",
        {
            "overall_passed": True,
            "gates": {
                "GATE-SG-1_stability": {"passed": True},
                "GATE-SG-2_resilience": {"passed": True},
                "GATE-SG-3_cost": {"passed": True},
                "GATE-SG-4_ops": {"passed": True},
            },
        },
    )

    _write_json(
        backend_root / "logs/service_governance/gate_sg1_window_report_20260313-000000_x.json",
        {
            "generated_at_epoch": 9999999999,
            "gate_result": {"passed": False},
        },
    )

    args = mod._build_parser().parse_args(
        [
            "--sg1-min-pass-count",
            "1",
            "--sg1-window-hours",
            "24",
        ]
    )

    report = mod.evaluate_readiness(args)
    assert report["sg1_window"]["actual_pass_count"] == 0
    assert report["closure_ready"] is False
