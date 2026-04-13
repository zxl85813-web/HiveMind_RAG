
import os
import json
from pathlib import Path
from loguru import logger

class EliteTraceHarvester:
    """
    L5 Distillation Hub: Collects high-quality (Golden) traces from Elite models 
    to serve as a training set for fine-tuning or few-shot learning in cheaper models.
    """
    def __init__(self, log_dir: str = "logs", dataset_path: str = "storage/datasets/golden_traces_v1.jsonl"):
        self.log_dir = Path(log_dir)
        self.dataset_path = Path(dataset_path)

    def harvest(self):
        logger.info("🏺 [Harvester] Harvesting Elite traces for distillation...")
        golden_count = 0
        
        # Ensure directory exists
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.dataset_path, "a", encoding="utf-8") as dataset:
            for log_file in self.log_dir.glob("*.log"):
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            record = json.loads(line).get("record", {})
                            extra = record.get("extra", {})
                            
                            # Filter for successful Elite-tier interactions
                            if extra.get("action") == "reviewer_experience":
                                meta = extra.get("meta", {})
                                if meta.get("priority", 0) >= 4 and meta.get("confidence_score", 0) > 0.9:
                                    # This is a GOLDEN trace
                                    synthetic_example = {
                                        "input": meta.get("query"),
                                        "target_model": meta.get("model"),
                                        "ideal_output": meta.get("summary"),
                                        "meta": {
                                            "trace_id": meta.get("trace_id"),
                                            "priority": meta.get("priority")
                                        }
                                    }
                                    dataset.write(json.dumps(synthetic_example, ensure_ascii=False) + "\n")
                                    golden_count += 1
                        except: continue
        
        logger.success(f"🏺 Harvested {golden_count} new golden traces for future model enhancement.")

if __name__ == "__main__":
    harvester = EliteTraceHarvester()
    harvester.harvest()
