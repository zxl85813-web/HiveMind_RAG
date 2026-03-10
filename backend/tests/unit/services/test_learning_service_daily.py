from pathlib import Path

import pytest

from app.core.config import settings
from app.services.learning_service import LearningService


@pytest.mark.anyio
async def test_daily_learning_cycle_generates_report(tmp_path: Path) -> None:
    original_dir = settings.SELF_LEARNING_REPORT_DIR
    original_token = settings.GITHUB_TOKEN
    original_project_owner = settings.GITHUB_PROJECT_OWNER
    original_project_number = settings.GITHUB_PROJECT_NUMBER

    settings.SELF_LEARNING_REPORT_DIR = str(tmp_path.name)
    settings.GITHUB_TOKEN = ""
    settings.GITHUB_PROJECT_OWNER = ""
    settings.GITHUB_PROJECT_NUMBER = 0

    try:
        result = await LearningService.run_daily_learning_cycle()
        report_path = LearningService._repo_root() / result.report_path
        assert report_path.exists()
        text = report_path.read_text(encoding="utf-8")
        assert "Self Learning Report" in text
        assert "系统改进建议" in text
    finally:
        settings.SELF_LEARNING_REPORT_DIR = original_dir
        settings.GITHUB_TOKEN = original_token
        settings.GITHUB_PROJECT_OWNER = original_project_owner
        settings.GITHUB_PROJECT_NUMBER = original_project_number
