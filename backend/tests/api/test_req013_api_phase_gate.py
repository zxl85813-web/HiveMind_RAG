import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_req013_api_phase_gate(client, admin_token):
    """
    [REQ-013] API Tier: 验证 Phase 1 的准出网关能正确识别基线延迟指标
    目标：APIEndpoint
    """
    # 模拟 HMER Phase 0 提交基线数据
    payload = {
        "metrics": [{"name": "TTFT (Baseline)", "value": 250.0, "context": {"grp": "phase-1"}}],
        "session_id": "test_req013"
    }
    resp_post = await client.post(
        "/api/v1/observability/baseline",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_post.status_code == 200

    # 验证准出网关能够返回状态
    resp_gate = await client.get(
        "/api/v1/observability/baseline/phase-gate/1",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_gate.status_code == 200
    data = resp_gate.json()["data"]
    assert "ready_to_proceed" in data
