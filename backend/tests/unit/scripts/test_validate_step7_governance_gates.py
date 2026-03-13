from scripts.validate_step7_governance_gates import evaluate_step7


def _base_sg007() -> dict:
    return {
        "run": {"duration_sec": 3600},
        "global": {
            "error_budget_consumed": 0.1,
            "degrade_trigger_ratio": 0.2,
            "avg_mttr_sec": 12.0,
        },
        "scenarios": [
            {
                "name": "steady",
                "error_budget_consumed": 0.01,
            }
        ],
    }


def _base_step3() -> dict:
    return {
        "overall_success": True,
        "results": [
            {"dependency": "llm", "convergence_ms": 2000},
            {"dependency": "es", "convergence_ms": 2500},
            {"dependency": "neo4j", "convergence_ms": 2400},
        ],
    }


def test_step7_passes_with_reasonable_thresholds():
    sg3 = {
        "gate_result": {"passed": True},
        "metrics": {"cost_reduction_ratio": 0.2, "quality_delta": -0.01},
        "thresholds": {"min_cost_reduction_ratio": 0.1, "max_quality_regression": 0.03},
    }
    report = evaluate_step7(
        _base_sg007(),
        _base_step3(),
        sg3,
        None,
        max_error_budget=0.2,
        max_steady_block_ratio=0.05,
        min_run_duration_sec=1800,
        max_mttr_sec=60.0,
        max_convergence_ms=60000.0,
        max_degrade_trigger_ratio=0.5,
        required_ops_files=[],
    )

    assert report["overall_passed"] is True
    assert report["failed_gates"] == []


def test_step7_fails_duration_and_convergence():
    sg007 = _base_sg007()
    sg007["run"]["duration_sec"] = 120
    step3 = _base_step3()
    step3["results"][0]["convergence_ms"] = 90000

    report = evaluate_step7(
        sg007,
        step3,
        None,
        None,
        max_error_budget=0.2,
        max_steady_block_ratio=0.05,
        min_run_duration_sec=3600,
        max_mttr_sec=60.0,
        max_convergence_ms=60000.0,
        max_degrade_trigger_ratio=0.5,
        required_ops_files=[],
    )

    assert report["overall_passed"] is False
    assert "GATE-SG-1_stability" in report["failed_gates"]
    assert "GATE-SG-2_resilience" in report["failed_gates"]


def test_step7_fails_when_sg3_gate_fails():
    sg3 = {
        "gate_result": {"passed": False},
        "metrics": {"cost_reduction_ratio": 0.01, "quality_delta": -0.2},
        "thresholds": {"min_cost_reduction_ratio": 0.1, "max_quality_regression": 0.03},
    }

    report = evaluate_step7(
        _base_sg007(),
        _base_step3(),
        sg3,
        None,
        max_error_budget=0.2,
        max_steady_block_ratio=0.05,
        min_run_duration_sec=1800,
        max_mttr_sec=60.0,
        max_convergence_ms=60000.0,
        max_degrade_trigger_ratio=0.5,
        required_ops_files=[],
    )

    assert report["overall_passed"] is False
    assert "GATE-SG-3_cost" in report["failed_gates"]


def test_step7_fails_when_sg1_window_gate_fails():
    sg1 = {
        "gate_result": {"passed": False},
        "metrics": {"global_error_budget": 0.35},
    }
    sg3 = {
        "gate_result": {"passed": True},
        "metrics": {"cost_reduction_ratio": 0.3, "quality_delta": -0.01},
        "thresholds": {"min_cost_reduction_ratio": 0.1, "max_quality_regression": 0.03},
    }

    report = evaluate_step7(
        _base_sg007(),
        _base_step3(),
        sg3,
        sg1,
        max_error_budget=0.2,
        max_steady_block_ratio=0.05,
        min_run_duration_sec=1800,
        max_mttr_sec=60.0,
        max_convergence_ms=60000.0,
        max_degrade_trigger_ratio=0.5,
        required_ops_files=[],
    )

    assert report["overall_passed"] is False
    assert "GATE-SG-1_stability" in report["failed_gates"]
