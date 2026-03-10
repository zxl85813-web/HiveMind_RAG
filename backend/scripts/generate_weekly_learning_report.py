"""Generate weekly collaborative learning report (CL-3).

Auto-collected:
- reflection totals and active agents from swarm_reflections
- daily report file count from docs/learning/daily

Manual inputs (CLI args):
- PR review coverage metrics
- knowledge crystallization metrics
- gap closure metrics
- flywheel conversion metrics

Usage example:
    python backend/scripts/generate_weekly_learning_report.py \
      --total-prs 12 \
      --reviewed-prs-ge2 8 \
      --skill-updates 1 \
      --registry-updates 1 \
      --total-gaps 10 \
      --closed-gaps 6 \
      --liked-feedback-items 20 \
      --promoted-feedback-items 7
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
import sys

from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.database import async_session_factory  # noqa: E402
@dataclass
class WeeklyInputs:
    total_prs: int = 0
    reviewed_prs_ge2: int = 0
    skill_updates: int = 0
    registry_updates: int = 0
    total_gaps: int = 0
    closed_gaps: int = 0
    liked_feedback_items: int = 0
    promoted_feedback_items: int = 0


@dataclass
class WeeklyAutoStats:
    reflections_total: int
    active_agents: int
    daily_reports_count: int


def _safe_div(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _iso_week_label(target: date) -> str:
    iso_year, iso_week, _ = target.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _status(value: float, threshold: float) -> str:
    return "on_track" if value >= threshold else "at_risk"


async def _collect_auto_stats(start_date: date, end_date: date, repo_root: Path) -> WeeklyAutoStats:
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC).replace(tzinfo=None)
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC).replace(tzinfo=None)

    async with async_session_factory() as session:
        stmt = text(
            """
            SELECT agent_name
            FROM swarm_reflections
            WHERE created_at >= :start_dt AND created_at < :end_dt
            """
        )
        rows = (await session.execute(stmt, {"start_dt": start_dt, "end_dt": end_dt})).all()
        reflections_total = len(rows)
        active_agents = len({(row[0] or "") for row in rows if row[0]})

    daily_dir = repo_root / "docs" / "learning" / "daily"
    daily_reports_count = 0
    if daily_dir.exists():
        for file in daily_dir.glob("*.md"):
            try:
                d = date.fromisoformat(file.stem)
            except ValueError:
                continue
            if start_date <= d <= end_date:
                daily_reports_count += 1

    return WeeklyAutoStats(
        reflections_total=reflections_total,
        active_agents=active_agents,
        daily_reports_count=daily_reports_count,
    )


def _build_report(
    week_label: str,
    start_date: date,
    end_date: date,
    generated_at: datetime,
    auto_stats: WeeklyAutoStats,
    manual: WeeklyInputs,
) -> str:
    self_reflection_activity = _safe_div(auto_stats.reflections_total, auto_stats.active_agents)
    mutual_learning_coverage = _safe_div(manual.reviewed_prs_ge2, manual.total_prs)
    knowledge_crystallization_rate = manual.skill_updates + manual.registry_updates
    gap_closure_rate = _safe_div(manual.closed_gaps, manual.total_gaps)
    flywheel_conversion_rate = _safe_div(manual.promoted_feedback_items, manual.liked_feedback_items)

    lines: list[str] = []
    lines.append(f"# Weekly Collaborative Learning Report - {week_label}")
    lines.append("")
    lines.append("## Period")
    lines.append("")
    lines.append(f"- Start: {start_date.isoformat()}")
    lines.append(f"- End: {end_date.isoformat()}")
    lines.append(f"- Generated At: {generated_at.replace(microsecond=0).isoformat()}Z")
    lines.append("")
    lines.append("## Snapshot")
    lines.append("")
    lines.append(f"- Reflections (total): {auto_stats.reflections_total}")
    lines.append(f"- Active agents: {auto_stats.active_agents}")
    lines.append(f"- Daily reports in period: {auto_stats.daily_reports_count}")
    lines.append("- Notes: Auto-filled for reflection baseline; complete manual fields below.")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value | Target | Formula | Source | Owner | Status |")
    lines.append("|:---|:---|:---|:---|:---|:---|:---|")
    lines.append(
        f"| Self-Reflection Activity | {self_reflection_activity:.2f} | >= 3.0 | weekly_reflections / active_agents | auto_db | Reflection Owner | {_status(self_reflection_activity, 3.0)} |"
    )
    lines.append(
        f"| Mutual Learning Coverage | {mutual_learning_coverage:.2%} | >= 60% | reviewed_prs_ge_2 / total_prs | manual | Team Lead | {_status(mutual_learning_coverage, 0.6)} |"
    )
    lines.append(
        f"| Knowledge Crystallization Rate | {knowledge_crystallization_rate} | >= 1 / month | skill_updates + registry_updates | manual | Governance Owner | {'on_track' if knowledge_crystallization_rate >= 1 else 'at_risk'} |"
    )
    lines.append(
        f"| Gap Closure Rate | {gap_closure_rate:.2%} | >= 50% | closed_gaps / total_gaps | mixed | Reflection Owner | {_status(gap_closure_rate, 0.5)} |"
    )
    lines.append(
        f"| Flywheel Conversion Rate | {flywheel_conversion_rate:.2%} | trend up | promoted_feedback_items / liked_feedback_items | manual | Team Lead | {'on_track' if flywheel_conversion_rate > 0 else 'at_risk'} |"
    )
    lines.append("")
    lines.append("## Detailed Inputs")
    lines.append("")
    lines.append(f"- total_prs: {manual.total_prs}")
    lines.append(f"- reviewed_prs_ge_2: {manual.reviewed_prs_ge2}")
    lines.append(f"- skill_updates: {manual.skill_updates}")
    lines.append(f"- registry_updates: {manual.registry_updates}")
    lines.append(f"- total_gaps: {manual.total_gaps}")
    lines.append(f"- closed_gaps: {manual.closed_gaps}")
    lines.append(f"- liked_feedback_items: {manual.liked_feedback_items}")
    lines.append(f"- promoted_feedback_items: {manual.promoted_feedback_items}")
    lines.append("")
    lines.append("## Actions For Next Week")
    lines.append("")
    lines.append("1. Fill low-confidence manual metrics and verify owners.")
    lines.append("2. Create one issue for each at_risk metric with due date.")
    lines.append("3. Review closure quality for GAP->INSIGHT pairing outcomes.")
    lines.append("")
    lines.append("## Appendix")
    lines.append("")
    lines.append("- Formula reference: docs/guides/collaborative_learning_metrics.md")
    lines.append("- Generated with: backend/scripts/generate_weekly_learning_report.py")
    lines.append("")

    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly collaborative learning report")
    parser.add_argument("--end-date", default=date.today().isoformat(), help="End date in YYYY-MM-DD (default: today)")
    parser.add_argument("--days", type=int, default=7, help="Window size in days (default: 7)")

    parser.add_argument("--total-prs", type=int, default=0)
    parser.add_argument("--reviewed-prs-ge2", type=int, default=0)
    parser.add_argument("--skill-updates", type=int, default=0)
    parser.add_argument("--registry-updates", type=int, default=0)
    parser.add_argument("--total-gaps", type=int, default=0)
    parser.add_argument("--closed-gaps", type=int, default=0)
    parser.add_argument("--liked-feedback-items", type=int, default=0)
    parser.add_argument("--promoted-feedback-items", type=int, default=0)

    args = parser.parse_args()

    end_date = date.fromisoformat(args.end_date)
    start_date = end_date - timedelta(days=max(1, args.days) - 1)
    week_label = _iso_week_label(end_date)

    repo_root = BASE_DIR.parent
    auto_stats = await _collect_auto_stats(start_date=start_date, end_date=end_date, repo_root=repo_root)

    manual = WeeklyInputs(
        total_prs=args.total_prs,
        reviewed_prs_ge2=args.reviewed_prs_ge2,
        skill_updates=args.skill_updates,
        registry_updates=args.registry_updates,
        total_gaps=args.total_gaps,
        closed_gaps=args.closed_gaps,
        liked_feedback_items=args.liked_feedback_items,
        promoted_feedback_items=args.promoted_feedback_items,
    )

    report = _build_report(
        week_label=week_label,
        start_date=start_date,
        end_date=end_date,
        generated_at=datetime.now(UTC),
        auto_stats=auto_stats,
        manual=manual,
    )

    weekly_dir = repo_root / "docs" / "learning" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    report_path = weekly_dir / f"{week_label}.md"
    report_path.write_text(report, encoding="utf-8")

    rel_path = report_path.relative_to(repo_root).as_posix()
    print(f"[CL-3] Weekly report generated: {rel_path}")


if __name__ == "__main__":
    asyncio.run(main())
