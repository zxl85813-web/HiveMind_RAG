from scripts.run_sg007_governance_drills import ScenarioResult, build_summary, evaluate_gate, render_markdown


def test_build_summary_and_markdown_basic_shape():
    results = [
        ScenarioResult(
            name="steady",
            total_requests=100,
            successful_requests=96,
            blocked_requests=4,
            degrade_triggers=6,
            mttr_sec=0.0,
            notes=["ok"],
        ),
        ScenarioResult(
            name="chaos",
            total_requests=20,
            successful_requests=15,
            blocked_requests=5,
            degrade_triggers=8,
            mttr_sec=2.5,
            notes=["outage"],
        ),
    ]

    summary = build_summary(results)

    assert summary["global"]["total_requests"] == 120
    assert summary["global"]["total_blocked"] == 9
    assert 0.0 <= summary["global"]["error_budget_consumed"] <= 1.0
    assert summary["global"]["avg_mttr_sec"] == 2.5

    md = render_markdown(summary)
    assert "SG-007 Drill Report" in md
    assert "Scenario Table" in md
    assert "Gate Hints" in md


def test_evaluate_gate_detects_violation_and_pass():
    results = [
        ScenarioResult(
            name="steady",
            total_requests=100,
            successful_requests=98,
            blocked_requests=2,
            degrade_triggers=5,
            mttr_sec=1.0,
            notes=["ok"],
        )
    ]
    summary = build_summary(results)

    passed = evaluate_gate(
        summary,
        max_error_budget=0.2,
        max_degrade_trigger_ratio=0.2,
        max_mttr_sec=5.0,
    )
    assert passed["enabled"] is True
    assert passed["passed"] is True
    assert passed["violations"] == []

    failed = evaluate_gate(
        summary,
        max_error_budget=0.01,
        max_degrade_trigger_ratio=0.02,
        max_mttr_sec=0.5,
    )
    assert failed["enabled"] is True
    assert failed["passed"] is False
    assert len(failed["violations"]) >= 1
