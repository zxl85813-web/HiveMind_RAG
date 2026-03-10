"""Run one self-learning cycle and print the generated report path.

Usage:
    python backend/scripts/run_daily_learning_cycle.py
"""

import asyncio
from pathlib import Path
import sys

# Ensure backend/app import path works when run from repository root.
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.services.learning_service import LearningService  # noqa: E402


async def main() -> None:
    result = await LearningService.run_daily_learning_cycle()
    print(f"[SELF-LEARNING] Report generated: {result.report_path}")
    print(f"[SELF-LEARNING] Suggestions: {len(result.suggestions)}")


if __name__ == "__main__":
    asyncio.run(main())
