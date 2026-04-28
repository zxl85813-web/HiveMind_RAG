"""
Root conftest — 仅放通用配置和 markers，不导入 app。
具体 fixtures 按层级放在 unit/conftest.py 和 integration/conftest.py 中。
"""
import os
import pytest

# 确保测试环境标记在任何 app 导入之前设置
os.environ["TESTING"] = "1"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("LLM_API_KEY", "sk-test")
os.environ.setdefault("LLM_PROVIDER", "siliconflow")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("LLM_BASE_URL", "https://example.com/v1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci")
os.environ.setdefault("VECTOR_STORE_TYPE", "chroma")


def pytest_configure(config):
    """注册自定义 markers。"""
    config.addinivalue_line("markers", "unit: 单元测试 (快速, 无外部依赖)")
    config.addinivalue_line("markers", "integration: 集成测试 (需要 DB)")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "slow: 慢速测试 (> 5s)")
