import pytest
from app.sdk.core.token_service import TokenService

class TestTokenService:
    """
    L1 Unit Tests for TokenService.
    Graph-Linked: [REQ-014-Context_Budget_Enforcement] -> [AAA-SDK-001]
    """

    @pytest.mark.graph(req="REQ-014", asset="AAA-SDK-001")
    def test_count_tokens_basic(self):
        """Contract View: Ensure token counting works for simple strings."""
        text = "Hello, HiveMind!"
        count = TokenService.count_tokens(text)
        assert count > 0
        assert count < 10

    @pytest.mark.graph(req="REQ-014")
    def test_count_tokens_empty(self):
        """Edge Case: Empty or None input."""
        assert TokenService.count_tokens("") == 0
        assert TokenService.count_tokens(None) == 0

    @pytest.mark.graph(req="REQ-014")
    def test_truncate_no_action_needed(self):
        """Logic View: Should return original text if within budget."""
        text = "Short text."
        budget = 100
        result = TokenService.truncate_to_budget(text, budget)
        assert result == text

    @pytest.mark.graph(req="REQ-014")
    def test_truncate_hard_cut(self):
        """Logic View: Should truncate and respect total budget (Fix for loop bug)."""
        text = "This is a much longer text that will definitely exceed a very small budget."
        budget = 10 # Small budget
        result = TokenService.truncate_to_budget(text, budget)
        
        assert "[Truncated due to context budget]" in result
        # VERIFICATION: The TOTAL token count (text + suffix) must be <= budget
        final_count = TokenService.count_tokens(result)
        assert final_count <= budget, f"Expected <= {budget}, but got {final_count}"

    @pytest.mark.graph(req="REQ-014")
    def test_truncate_at_newline(self):
        """Logic View: Should prefer truncating at a newline for semantic readability."""
        text = "Line 1\n" * 50 # Definitely > 100 tokens
        budget = 50 
        
        result = TokenService.truncate_to_budget(text, budget)
        assert "Line 1" in result
        assert "[Truncated due to context budget]" in result
        # Ensure it has fewer lines than original
        assert result.count("\n") < 50

    @pytest.mark.graph(req="REQ-014")
    def test_calculate_budget_plan(self):
        """Business View: Verify budget ratios (from REQ-014 design)."""
        plan = TokenService.calculate_budget_plan(total_window=1000)
        
        assert plan["system_prompt"] == 100 # 10%
        assert plan["memory"] == 150        # 15%
        assert plan["rag_context"] == 450   # 45%
        assert plan["history"] == 200       # 20%
        assert plan["output"] == 100        # 10%
