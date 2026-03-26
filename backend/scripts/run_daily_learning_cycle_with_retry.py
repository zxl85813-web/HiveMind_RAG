"""Run daily learning cycle with retries and log persistence.

Usage:
    python backend/scripts/run_daily_learning_cycle_with_retry.py --retries 3 --delay-seconds 15
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Ensure backend/app import path works when run from repository root.
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("daily_learning_retry")
t_logger = get_trace_logger("scripts.daily_learning_retry")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

from app.services.learning_service import LearningService  # noqa: E402


def _log_path() -> Path:
    repo_root = backend_dir.parent
    log_dir = repo_root / "docs" / "learning" / "daily" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{datetime.now(UTC).date().isoformat()}.log"


def _append_log(message: str) -> None:
    ts = datetime.now(UTC).replace(microsecond=0).isoformat()
    line = f"[{ts}] {message}\n"
    _log_path().open("a", encoding="utf-8").write(line)


async def main(retries: int, delay_seconds: int) -> None:
    t_logger.info(f"🚀 Starting daily learning cycle with retry (max {retries})...", action="retry_start")
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            _append_log(f"attempt={attempt} status=start")
            t_logger.info(f"🔄 Attempting cycle {attempt}/{attempts}...", action="retry_attempt", meta={"attempt": attempt})
            
            result = await LearningService.run_daily_learning_cycle()
            
            _append_log(
                f"attempt={attempt} status=success report={result.report_path} suggestions={len(result.suggestions)}"
            )
            t_logger.success(
                f"✅ Cycle success on attempt {attempt}.",
                action="retry_success",
                meta={
                    "attempt": attempt,
                    "report": result.report_path,
                    "suggestions": len(result.suggestions)
                }
            )
            return
        except Exception as exc:
            _append_log(f"attempt={attempt} status=error error={exc!s}")
            t_logger.warning(
                f"⚠️ Attempt {attempt} failed: {exc!s}",
                action="retry_failure",
                meta={"attempt": attempt, "error": str(exc)}
            )
            if attempt >= attempts:
                t_logger.error("🛑 All retry attempts exhausted.", action="retry_exhausted")
                raise
            await asyncio.sleep(max(1, delay_seconds))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily learning cycle with retries")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--delay-seconds", type=int, default=15)
    args = parser.parse_args()
    asyncio.run(main(args.retries, args.delay_seconds))
