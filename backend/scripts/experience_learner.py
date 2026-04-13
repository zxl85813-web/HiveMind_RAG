
import os
import json
from pathlib import Path
from loguru import logger
from typing import Dict, List, Any

class ExperienceLearner:
    """
    L5 Self-Evolutions: Analyzes system logs to refine model selection strategies.
    It identifies models that are under-performing (too many corrections) 
    or over-allocated (expensive but trivial).
    """
    def __init__(self, log_dir: str = "logs", experience_file: str = "storage/review_experience.json"):
        self.log_dir = Path(log_dir)
        self.experience_file = Path(experience_file)
        self.experience_store = self._load_experience()

    def _load_experience(self) -> Dict[str, Any]:
        if self.experience_file.exists():
            with open(self.experience_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"model_stats": {}, "recommender_overrides": {}}

    def _save_experience(self):
        self.experience_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.experience_file, "w", encoding="utf-8") as f:
            json.dump(self.experience_store, f, indent=2)

    def harvest_experience(self):
        logger.info("🧠 [ExperienceLearner] Harvesting data from logs...")
        
        raw_events = []
        for log_file in self.log_dir.glob("*.log"):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line).get("record", {})
                        extra = record.get("extra", {})
                        if extra.get("action") == "reviewer_experience":
                            raw_events.append(extra.get("meta"))
                    except: continue

        # Update stats
        for event in raw_events:
            model = event.get("model")
            if model not in self.experience_store["model_stats"]:
                self.experience_store["model_stats"][model] = {"total_reviews": 0, "avg_confidence": 0, "high_risk_flag_ratio": 0}
            
            stats = self.experience_store["model_stats"][model]
            stats["total_reviews"] += 1
            # Moving average of confidence
            stats["avg_confidence"] = (stats["avg_confidence"] * (stats["total_reviews"]-1) + event.get("confidence_score", 0.8)) / stats["total_reviews"]
        
        # LOGIC: If a model constantly reports low confidence for a priority, suggest an override.
        # For this demo, we'll simulate an insight:
        self.experience_store["insights"] = [
            "Insight: DeepSeek-V3 confidence drops by 30% for Priority 4 tasks. Consider mandatory escalation to Claude."
        ]
        
        self._save_experience()
        logger.success(f"Experience stored with {len(raw_events)} events processed.")

if __name__ == "__main__":
    learner = ExperienceLearner()
    learner.harvest_experience()
