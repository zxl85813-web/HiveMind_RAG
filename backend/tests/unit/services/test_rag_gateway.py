"""
RAGGateway 单元测试。

覆盖:
    - 正常检索 (单 KB / 多 KB)
    - 熔断器 (Circuit Breaker) 逻辑
    - 降级与警告
    - 并行检索异常处理
"""
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.rag_gateway import RAGGateway
from app.schemas.knowledge_protocol import KnowledgeFragment


@pytest.fixture
def gateway():
    """每个测试创建新的 gateway 实例，避免状态污染。"""
    gw = RAGGateway()
    gw._circuit_breakers = {}  # 重置熔断器状态
    return gw


# ---------------------------------------------------------------------------
# Normal Retrieval
# ---------------------------------------------------------------------------

class TestRetrieve:

    @pytest.mark.asyncio
    async def test_retrieve_single_kb(self, gateway):
        result = await gateway.retrieve("test query", kb_ids=["kb_1"])
        assert result.total_found >= 1
        assert result.query == "test query"
        assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_retrieve_multiple_kbs(self, gateway):
        result = await gateway.retrieve("test", kb_ids=["kb_1", "kb_2", "kb_3"])
        assert result.total_found >= 3
        assert all(f.kb_id in ["kb_1", "kb_2", "kb_3"] for f in result.fragments)

    @pytest.mark.asyncio
    async def test_retrieve_empty_kb_list(self, gateway):
        result = await gateway.retrieve("test", kb_ids=[])
        assert result.total_found == 0
        assert "No active KBs" in result.warnings[0]


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:

    def test_circuit_starts_closed(self, gateway):
        assert not gateway._is_circuit_open("kb_1")

    def test_circuit_opens_after_max_failures(self, gateway):
        for _ in range(gateway.max_failures):
            gateway._record_failure("kb_1")
        assert gateway._is_circuit_open("kb_1")

    def test_circuit_stays_closed_below_threshold(self, gateway):
        for _ in range(gateway.max_failures - 1):
            gateway._record_failure("kb_1")
        assert not gateway._is_circuit_open("kb_1")

    def test_success_resets_failure_count(self, gateway):
        gateway._record_failure("kb_1")
        gateway._record_failure("kb_1")
        gateway._record_success("kb_1")
        assert gateway._circuit_breakers["kb_1"]["fail_count"] == 0
        assert gateway._circuit_breakers["kb_1"]["state"] == "CLOSED"

    def test_circuit_half_open_after_timeout(self, gateway):
        for _ in range(gateway.max_failures):
            gateway._record_failure("kb_1")
        # 模拟超时
        gateway._circuit_breakers["kb_1"]["last_fail_time"] = time.time() - gateway.recovery_timeout - 1
        assert not gateway._is_circuit_open("kb_1")  # 进入 HALF-OPEN
        assert gateway._circuit_breakers["kb_1"]["state"] == "HALF-OPEN"

    @pytest.mark.asyncio
    async def test_tripped_kb_skipped_in_retrieval(self, gateway):
        # 触发 kb_2 熔断
        for _ in range(gateway.max_failures):
            gateway._record_failure("kb_2")

        result = await gateway.retrieve("test", kb_ids=["kb_1", "kb_2"])
        # kb_2 应被跳过，只有 kb_1 的结果
        assert any("kb_2" in w for w in result.warnings)
        assert all(f.kb_id != "kb_2" for f in result.fragments)
