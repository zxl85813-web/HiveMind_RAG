import argparse

from scripts.validate_step5_sg3_cost_quality import evaluate_cost_quality


def _args(**overrides):
    base = {
        "samples": 120,
        "seed": 42,
        "baseline": "premium",
        "premium_input_cost_per_1k": 0.006,
        "premium_output_cost_per_1k": 0.018,
        "eco_input_cost_per_1k": 0.001,
        "eco_output_cost_per_1k": 0.002,
        "max_quality_regression": 0.03,
        "min_cost_reduction_ratio": 0.05,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_sg3_report_contains_gate_result_and_metrics():
    report = evaluate_cost_quality(_args())

    assert "metrics" in report
    assert "gate_result" in report
    assert "thresholds" in report
    assert report["samples"] == 120


def test_sg3_gate_fails_with_too_strict_cost_target():
    report = evaluate_cost_quality(_args(min_cost_reduction_ratio=0.95))
    assert report["gate_result"]["passed"] is False
    assert report["gate_result"]["cost_gate_passed"] is False
