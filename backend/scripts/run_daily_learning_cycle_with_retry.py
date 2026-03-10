"""Run daily learning cycle with retries and log persistence.

Usage:
    python backend/scripts/run_daily_learning_cycle_with_retry.py --retries 3 --delay-seconds 15
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.services.learning_service import LearningService  # noqa: E402


def _log_path() -> Path:
    repo_root = BASE_DIR.parent
    log_dir = repo_root / "docs" / "learning" / "daily" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{datetime.now(UTC).date().isoformat()}.log"


def _append_log(message: str) -> None:
    ts = datetime.now(UTC).replace(microsecond=0).isoformat()
    line = f"[{ts}] {message}\n"
    _log_path().open("a", encoding="utf-8").write(line)


async def main(retries: int, delay_seconds: int) -> None:
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            _append_log(f"attempt={attempt} status=start")
            result = await LearningService.run_daily_learning_cycle()
            _append_log(
                f"attempt={attempt} status=success report={result.report_path} suggestions={len(result.suggestions)}"
            )
            print(f"[SELF-LEARNING] Report generated: {result.report_path}")
            print(f"[SELF-LEARNING] Suggestions: {len(result.suggestions)}")
            return
        except Exception as exc:  # noqa: BLE001
            _append_log(f"attempt={attempt} status=error error={exc!s}")
            if attempt >= attempts:
                raise
            await asyncio.sleep(max(1, delay_seconds))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily learning cycle with retries")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--delay-seconds", type=int, default=15)
    args = parser.parse_args()
    asyncio.run(main(args.retries, args.delay_seconds))
