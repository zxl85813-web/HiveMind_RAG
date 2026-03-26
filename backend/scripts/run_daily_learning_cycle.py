"""Run one self-learning cycle and print the generated report path.

Usage:
    python backend/scripts/run_daily_learning_cycle.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend/app import path works when run from repository root.
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("daily_learning")
t_logger = get_trace_logger("scripts.daily_learning")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

from app.services.learning_service import LearningService  # noqa: E402


async def main() -> None:
    t_logger.info("🚀 Starting daily learning cycle...", action="cycle_start")
    try:
        result = await LearningService.run_daily_learning_cycle()
        t_logger.success(
            "✅ Daily learning cycle completed.",
            action="cycle_success",
            meta={
                "report": result.report_path,
                "suggestions": len(result.suggestions)
            }
        )
    except Exception as e:
        t_logger.error(f"❌ Daily learning cycle failed: {e!s}", action="cycle_error")
        raise


if __name__ == "__main__":
    asyncio.run(main())
