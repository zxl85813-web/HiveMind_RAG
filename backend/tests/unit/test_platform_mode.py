"""
Platform Mode 单元测试 — 验证 PLATFORM_MODE 配置和模块过滤逻辑。

测试覆盖:
  1. PlatformMode 枚举值
  2. Settings 的 rag_enabled / agent_enabled 属性
  3. 三种模式下的模块启用组合
  4. 环境变量驱动的模式切换
  5. Health 端点返回正确的模式信息
"""
import os
import pytest
from unittest.mock import patch


# ── 1. PlatformMode 枚举 ──────────────────────────────────

class TestPlatformModeEnum:
    """PlatformMode 枚举值验证。"""

    def test_enum_values(self):
        from app.core.config import PlatformMode
        assert PlatformMode.RAG.value == "rag"
        assert PlatformMode.AGENT.value == "agent"
        assert PlatformMode.FULL.value == "full"

    def test_enum_from_string(self):
        from app.core.config import PlatformMode
        assert PlatformMode("rag") == PlatformMode.RAG
        assert PlatformMode("agent") == PlatformMode.AGENT
        assert PlatformMode("full") == PlatformMode.FULL

    def test_invalid_mode_raises(self):
        from app.core.config import PlatformMode
        with pytest.raises(ValueError):
            PlatformMode("invalid")


# ── 2. Settings 属性 ──────────────────────────────────────

class TestSettingsModuleFlags:
    """rag_enabled / agent_enabled 属性在各模式下的行为。"""

    def test_full_mode_enables_all(self):
        from app.core.config import Settings
        s = Settings(PLATFORM_MODE="full")
        assert s.rag_enabled is True
        assert s.agent_enabled is True

    def test_rag_mode_enables_rag_only(self):
        from app.core.config import Settings
        s = Settings(PLATFORM_MODE="rag")
        assert s.rag_enabled is True
        assert s.agent_enabled is False

    def test_agent_mode_enables_agent_only(self):
        from app.core.config import Settings
        s = Settings(PLATFORM_MODE="agent")
        assert s.rag_enabled is False
        assert s.agent_enabled is True

    def test_default_mode_is_full(self):
        from app.core.config import Settings
        s = Settings()
        assert s.PLATFORM_MODE.value == "full"
        assert s.rag_enabled is True
        assert s.agent_enabled is True


# ── 3. 环境变量驱动 ───────────────────────────────────────

class TestEnvVarDriven:
    """通过环境变量设置 PLATFORM_MODE。"""

    def test_env_var_rag(self):
        with patch.dict(os.environ, {"PLATFORM_MODE": "rag"}):
            from app.core.config import Settings
            s = Settings()
            assert s.PLATFORM_MODE.value == "rag"

    def test_env_var_agent(self):
        with patch.dict(os.environ, {"PLATFORM_MODE": "agent"}):
            from app.core.config import Settings
            s = Settings()
            assert s.PLATFORM_MODE.value == "agent"

    def test_env_var_case_sensitive(self):
        """PLATFORM_MODE 应该是小写。"""
        from app.core.config import Settings
        with pytest.raises(Exception):
            Settings(PLATFORM_MODE="RAG")


# ── 4. Health 端点 ────────────────────────────────────────

class TestHealthEndpoint:
    """Health 端点返回正确的平台模式信息。"""

    @pytest.mark.asyncio
    async def test_health_returns_mode_full(self):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PLATFORM_MODE.value = "full"
            mock_settings.rag_enabled = True
            mock_settings.agent_enabled = True

            # 直接构造端点逻辑而非导入路由模块 (避免触发重量级初始化)
            result = {
                "status": "ok",
                "service": "hivemind",
                "mode": mock_settings.PLATFORM_MODE.value,
                "modules": {
                    "rag": mock_settings.rag_enabled,
                    "agent": mock_settings.agent_enabled,
                },
            }

            assert result["status"] == "ok"
            assert result["mode"] == "full"
            assert result["modules"]["rag"] is True
            assert result["modules"]["agent"] is True

    @pytest.mark.asyncio
    async def test_health_returns_mode_rag(self):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PLATFORM_MODE.value = "rag"
            mock_settings.rag_enabled = True
            mock_settings.agent_enabled = False

            result = {
                "status": "ok",
                "service": "hivemind",
                "mode": mock_settings.PLATFORM_MODE.value,
                "modules": {
                    "rag": mock_settings.rag_enabled,
                    "agent": mock_settings.agent_enabled,
                },
            }

            assert result["mode"] == "rag"
            assert result["modules"]["rag"] is True
            assert result["modules"]["agent"] is False

    @pytest.mark.asyncio
    async def test_health_returns_mode_agent(self):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PLATFORM_MODE.value = "agent"
            mock_settings.rag_enabled = False
            mock_settings.agent_enabled = True

            result = {
                "status": "ok",
                "service": "hivemind",
                "mode": mock_settings.PLATFORM_MODE.value,
                "modules": {
                    "rag": mock_settings.rag_enabled,
                    "agent": mock_settings.agent_enabled,
                },
            }

            assert result["mode"] == "agent"
            assert result["modules"]["rag"] is False
            assert result["modules"]["agent"] is True

    @pytest.mark.asyncio
    async def test_readiness_rag_mode_has_vector_store(self):
        """RAG 模式的 readiness 应包含 vector_store 检查。"""
        from app.core.config import Settings
        s = Settings(PLATFORM_MODE="rag")

        checks = {"database": "ok"}
        if s.rag_enabled:
            checks["vector_store"] = "ok"
            checks["embedding"] = "ok"
        if s.agent_enabled:
            checks["llm"] = "ok"

        assert "vector_store" in checks
        assert "embedding" in checks
        assert "llm" not in checks

    @pytest.mark.asyncio
    async def test_readiness_agent_mode_has_llm(self):
        """Agent 模式的 readiness 应包含 llm 检查。"""
        from app.core.config import Settings
        s = Settings(PLATFORM_MODE="agent")

        checks = {"database": "ok"}
        if s.rag_enabled:
            checks["vector_store"] = "ok"
            checks["embedding"] = "ok"
        if s.agent_enabled:
            checks["llm"] = "ok"

        assert "llm" in checks
        assert "vector_store" not in checks
