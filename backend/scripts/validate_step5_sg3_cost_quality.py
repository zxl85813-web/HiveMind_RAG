"""
Phase 5 / TASK-SG-006 / GATE-SG-3 cost-quality validator.

Generates synthetic workload evidence for:
- cost reduction after smart routing
- quality non-regression within configurable threshold
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.services.claw_router_governance import ClawRouterGovernance


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate SG-3 cost-quality gate with synthetic workload")
    parser.add_argument("--samples", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--baseline", choices=["premium", "eco"], default="premium")
    parser.add_argument("--premium-input-cost-per-1k", type=float, default=0.006)
    parser.add_argument("--premium-output-cost-per-1k", type=float, default=0.018)
    parser.add_argument("--eco-input-cost-per-1k", type=float, default=0.001)
    parser.add_argument("--eco-output-cost-per-1k", type=float, default=0.002)
    parser.add_argument("--max-quality-regression", type=float, default=0.03)
    parser.add_argument("--min-cost-reduction-ratio", type=float, default=0.10)
    parser.add_argument("--output-json", default="logs/service_governance/step5_sg3_cost_quality_report.json")
    parser.add_argument("--output-md", default="logs/service_governance/step5_sg3_cost_quality_report.md")
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


def _estimate_cost(tokens_in: int, tokens_out: int, *, tier: str, args: argparse.Namespace) -> float:
    if tier == "premium":
        in_cost = args.premium_input_cost_per_1k
        out_cost = args.premium_output_cost_per_1k
    else:
        in_cost = args.eco_input_cost_per_1k
        out_cost = args.eco_output_cost_per_1k
    return (tokens_in / 1000.0) * in_cost + (tokens_out / 1000.0) * out_cost


def _required_tier_from_prompt(prompt: str, expected_tokens: int) -> str:
    lowered = prompt.lower()
    hard_markers = ["architecture", "tradeoff", "debug", "root cause", "urgent", "p0", "线上", "紧急", "推理"]
    if any(marker in lowered for marker in hard_markers):
        return "premium"
    if expected_tokens >= 2200:
        return "premium"
    return "eco"


def _quality_score(chosen_tier: str, required_tier: str) -> float:
    if required_tier == "premium" and chosen_tier == "eco":
        return 0.97
    return 1.0


def _build_prompt(i: int, rng: random.Random) -> tuple[str, int, int]:
    base_templates = [
        "quick status update for service health and deployment check",
        "please summarize recent logs and provide concise action items",
        "architecture tradeoff analysis for retrieval split and fallback strategy",
        "urgent root cause debug for production timeout and retry storm",
        "design a benchmark matrix for cost latency and quality",
        "low cost operation review and optimization suggestions",
    ]
    prompt = base_templates[i % len(base_templates)]

    token_in = int(rng.randint(180, 3200))
    if i % 7 == 0:
        token_in = int(rng.randint(2200, 4200))
    token_out = max(80, int(token_in * rng.uniform(0.25, 0.45)))

    expanded = prompt + " " + ("data " * max(1, token_in // 40))
    return expanded, token_in, token_out


def evaluate_cost_quality(args: argparse.Namespace) -> dict[str, Any]:
    rng = random.Random(args.seed)
    router = ClawRouterGovernance()

    baseline_total_cost = 0.0
    router_total_cost = 0.0
    baseline_quality_scores: list[float] = []
    router_quality_scores: list[float] = []
    tier_counts = {"eco": 0, "premium": 0}

    for i in range(args.samples):
        prompt, token_in, token_out = _build_prompt(i, rng)
        required_tier = _required_tier_from_prompt(prompt, token_in)

        baseline_tier = args.baseline
        baseline_total_cost += _estimate_cost(token_in, token_out, tier=baseline_tier, args=args)
        baseline_quality_scores.append(_quality_score(baseline_tier, required_tier))

        decision = router.decide([{"role": "user", "content": prompt}])
        router_tier = str(decision["tier"])
        tier_counts[router_tier] += 1
        router_total_cost += _estimate_cost(token_in, token_out, tier=router_tier, args=args)
        router_quality_scores.append(_quality_score(router_tier, required_tier))

    baseline_avg_quality = sum(baseline_quality_scores) / len(baseline_quality_scores)
    router_avg_quality = sum(router_quality_scores) / len(router_quality_scores)
    quality_delta = router_avg_quality - baseline_avg_quality

    if baseline_total_cost <= 0:
        cost_reduction_ratio = 0.0
    else:
        cost_reduction_ratio = (baseline_total_cost - router_total_cost) / baseline_total_cost

    quality_gate_pass = quality_delta >= -args.max_quality_regression
    cost_gate_pass = cost_reduction_ratio >= args.min_cost_reduction_ratio
    gate_passed = quality_gate_pass and cost_gate_pass

    return {
        "generated_at_epoch": int(time.time()),
        "samples": args.samples,
        "baseline_strategy": args.baseline,
        "router_tier_counts": tier_counts,
        "metrics": {
            "baseline_total_cost": round(baseline_total_cost, 6),
            "router_total_cost": round(router_total_cost, 6),
            "cost_reduction_ratio": round(cost_reduction_ratio, 6),
            "baseline_avg_quality": round(baseline_avg_quality, 6),
            "router_avg_quality": round(router_avg_quality, 6),
            "quality_delta": round(quality_delta, 6),
        },
        "thresholds": {
            "min_cost_reduction_ratio": args.min_cost_reduction_ratio,
            "max_quality_regression": args.max_quality_regression,
        },
        "gate_result": {
            "passed": gate_passed,
            "cost_gate_passed": cost_gate_pass,
            "quality_gate_passed": quality_gate_pass,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    m = report["metrics"]
    t = report["thresholds"]
    g = report["gate_result"]

    lines = [
        "# Step-5 SG-3 Cost-Quality Report",
        "",
        f"- generated_at_epoch: {report['generated_at_epoch']}",
        f"- samples: {report['samples']}",
        f"- baseline_strategy: {report['baseline_strategy']}",
        f"- gate_passed: {g['passed']}",
        "",
        "## Metrics",
        "",
        f"- baseline_total_cost: {m['baseline_total_cost']}",
        f"- router_total_cost: {m['router_total_cost']}",
        f"- cost_reduction_ratio: {m['cost_reduction_ratio']}",
        f"- baseline_avg_quality: {m['baseline_avg_quality']}",
        f"- router_avg_quality: {m['router_avg_quality']}",
        f"- quality_delta: {m['quality_delta']}",
        "",
        "## Thresholds",
        "",
        f"- min_cost_reduction_ratio: {t['min_cost_reduction_ratio']}",
        f"- max_quality_regression: {t['max_quality_regression']}",
        "",
        "## Gate Evaluation",
        "",
        f"- cost_gate_passed: {g['cost_gate_passed']}",
        f"- quality_gate_passed: {g['quality_gate_passed']}",
        "",
        "## Router Tier Counts",
        "",
        f"- eco: {report['router_tier_counts']['eco']}",
        f"- premium: {report['router_tier_counts']['premium']}",
    ]
    return "\n".join(lines)


def main() -> None:
    args = _build_parser().parse_args()
    run_key = _build_run_key()

    report = evaluate_cost_quality(args)
    report["run_key"] = run_key

    output_json = backend_dir / args.output_json
    output_md = backend_dir / args.output_md
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")

    print(f"[SG-3] json report: {output_json}")
    print(f"[SG-3] markdown report: {output_md}")

    if not args.no_versioned:
        output_json_v = _versioned_path(output_json, run_key)
        output_md_v = _versioned_path(output_md, run_key)
        output_json_v.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md_v.write_text(render_markdown(report), encoding="utf-8")
        print(f"[SG-3] versioned json report: {output_json_v}")
        print(f"[SG-3] versioned markdown report: {output_md_v}")

    if args.enforce and not bool(report["gate_result"]["passed"]):
        print(f"[SG-3] gate failed: {report['gate_result']}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
