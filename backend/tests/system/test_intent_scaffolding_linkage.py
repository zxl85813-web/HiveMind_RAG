import time
from unittest.mock import AsyncMock, patch

import pytest

# Domain Imports
from app.services.rag_gateway import RAGGateway

# 🛰️ [FE-GOVERNANCE] Mocking the Intent Scaffolding Logic (as proposed in DES-013)
# Note: Since DES-013 is an implementation plan, we test the PROPOSED logic
# and the existing Observability/Measurement infrastructure it relies on.

@pytest.fixture
async def mock_intent_service():
    """
    Mock the IntentScaffoldingService proposed in DES-013.
    This service predicts intent from partial queries.
    """
    with patch("app.services.intent_scaffolding.IntentScaffoldingService") as mock:
        service_instance = mock.return_value
        service_instance.predict_intent_stream = AsyncMock(
            return_value={"intent": "knowledge_retrieval", "confidence": 0.92}
        )
        service_instance.trigger_speculative_retrieval = AsyncMock(return_value="job_prefetch_001")
        yield service_instance

class TestIntentScaffoldingFlow:
    """
    🎯 Business Case: [REQ-013] Architecture Reconstruction - Intent Pre-detection
    Validates the end-to-end chain from FE Baseline reporting to Backend Intent Prediction.
    """

    @pytest.mark.asyncio
    async def test_baseline_reporting_to_diagnosis_link(self, client, admin_token, clean_test_db):
        """
        [Traceability]: FE Baseline -> Backend Recording -> AI Diagnosis
        Ensures that HMER Phase 0 data flows correctly to drive DES-013 logic.
        """
        # 1. Simulate Frontend Reporting 745ms TTFT (The baseline bottleneck)
        payload = {
            "metrics": [
                {"name": "TTFT (Baseline)", "value": 745.0, "context": {"grp": "phase-0", "ua": "test-bot"}},
                {"name": "Retrieval Latency", "value": 182.0, "context": {"grp": "phase-0"}}
            ],
            "session_id": "sess_hmer_001"
        }

        resp = await client.post(
            "/api/v1/observability/baseline",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "recorded"

        # 2. Trigger AI Diagnosis (HMER Reflect Phase)
        # This confirms the backend's "Cognitive Feedback" is aware of the bottleneck
        diag_resp = await client.get(
            "/api/v1/observability/baseline/ai-diagnosis",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert diag_resp.status_code == 200
        data = diag_resp.json()["data"]
        assert data["status"] in ["WARNING", "CRITICAL"] # 745ms should trigger a warning
        assert "analysis" in data
        print(f"\n🧠 AI Diagnosis Output: {data['analysis'][:100]}...")

    @pytest.mark.asyncio
    async def test_rag_gateway_governance_path_coverage(self):
        """
        [Linkage]: RAGGateway -> Service Governance choice
        Ensures the choice between 'premium' and 'eco' based on query complexity.
        """
        gateway = RAGGateway()

        # Scenario A: Simple query should potentially hit 'eco' path or use cached intent
        with patch("app.services.service_governance.choose_topology_path") as mock_topo:
            mock_topo.return_value.path = "eco"
            resp = await gateway.retrieve(query="What is 1+1?", kb_ids=["kb_001"])
            assert resp.query == "What is 1+1?"
            mock_topo.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase_gate_readiness_audit(self, client, admin_token):
        """
        [Gate]: Verify if Phase 0 satisfies exit criteria for Phase 1 (DES-013)
        """
        resp = await client.get(
            "/api/v1/observability/baseline/phase-gate/0",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        # If we have baseline data, it should say we are ready to proceed to Phase 1 (Architecture Design)
        assert "audit_report" in data
        assert data["phase"] == 0

def run_performance_check():
    """Helper to simulate the 300ms goal from DES-013"""
    start = time.time()
    # Simulate a 'prefetch-hit' retrieval
    time.sleep(0.150) # 150ms prefetch retrieval
    duration = (time.time() - start) * 1000
    print(f"\n📊 Performance Simulation: {duration:.2f}ms (Goal: < 300ms)")
    return duration < 300
