
from typing import Any, Dict, List
from pydantic import BaseModel
from loguru import logger

class ModelProfile(BaseModel):
    name: str
    tier: int # 1: Fast, 2: Balanced, 3: Elite
    strengths: List[str]
    weaknesses: List[str]
    cost_per_1m_input: float # USD
    cost_per_1m_output: float # USD

MODEL_REGISTRY: Dict[str, ModelProfile] = {
    "deepseek-v3": ModelProfile(
        name="DeepSeek-V3",
        tier=1,
        strengths=["Coding", "High Speed", "Cost Effective"],
        weaknesses=["Complex Reasoning", "Nuance"],
        cost_per_1m_input=0.1,
        cost_per_1m_output=0.2
    ),
    "gpt-4o": ModelProfile(
        name="GPT-4o",
        tier=3,
        strengths=["Multi-modal", "Balanced reasoning", "Wide instruction following"],
        weaknesses=["Expensive", "High latency"],
        cost_per_1m_input=5.0,
        cost_per_1m_output=15.0
    ),
    "claude-3-5-sonnet": ModelProfile(
        name="Claude 3.5 Sonnet",
        tier=3,
        strengths=["Coding precision", "Nuanced reasoning", "Visual analysis"],
        weaknesses=["Usage limits", "Relatively high cost"],
        cost_per_1m_input=3.0,
        cost_per_1m_output=15.0
    ),
    "gemini-1.5-flash": ModelProfile(
        name="Gemini 1.5 Flash",
        tier=2,
        strengths=["Long context", "Low latency", "Free tier available"],
        weaknesses=["Less consistent reasoning than Pro"],
        cost_per_1m_input=0.075,
        cost_per_1m_output=0.3
    )
}

class ReviewGovernance:
    """
    L5 Economics: Matches tasks to the most cost-effective model based on priority and requirements.
    """
    @staticmethod
    def get_optimal_critic(priority: int, task_type: str = "general") -> ModelProfile:
        # 🧠 Experience-Based Overrides (L5 Learning)
        import json
        from pathlib import Path
        exp_file = Path("storage/review_experience.json")
        if exp_file.exists():
            try:
                with open(exp_file, "r") as f:
                    exp = json.load(f)
                    # Example override: "If DeepSeek is marked as weak for priority 3, upgrade"
                    if priority == 3 and exp.get("recommender_overrides", {}).get("upgrade_p3"):
                         return MODEL_REGISTRY.get("claude-3-5-sonnet")
            except: pass

        if priority >= 4:
            # Elite for high stake
            return MODEL_REGISTRY.get("claude-3-5-sonnet") or MODEL_REGISTRY["gpt-4o"]
        elif priority == 3:
            # Balanced for medium stake
            return MODEL_REGISTRY.get("gemini-1.5-flash") or MODEL_REGISTRY["deepseek-v3"]
        else:
            # Economy for low stake
            return MODEL_REGISTRY["deepseek-v3"]

    @staticmethod
    def get_governance_context(model_name: str) -> str:
        profile = MODEL_REGISTRY.get(model_name)
        if not profile:
            return ""
        return f"""
        ### 🧠 CRITIC SELF-PROFILE
        Model: {profile.name}
        Strengths: {', '.join(profile.strengths)}
        Weaknesses: {', '.join(profile.weaknesses)}
        Economic Impact: ${profile.cost_per_1m_input}/1M tokens (Input)
        
        When reviewing, acknowledge your strengths and weaknesses. 
        If a task is high priority but you occupy a 'weak' segment for it, recommend an escalation to a specialized swarm.
        """

review_governance = ReviewGovernance()
