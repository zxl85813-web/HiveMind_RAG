from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DesignResult(BaseModel):
    headers: List[str]
    rows: List[Dict[str, Any]]
    
class GenerationContext(BaseModel):
    """
    Context for Active Creating & Self-Correction Pipeline.
    """
    # Input
    task_description: str
    kb_ids: List[str]
    
    # State
    retrieved_content: List[str] = Field(default_factory=list)
    draft_content: Optional[DesignResult] = None
    feedback_log: List[str] = Field(default_factory=list)
    
    # Output
    final_artifact_path: Optional[str] = None
    
    def log(self, step: str, message: str):
        # print(f"[{step}] {message}")
        self.feedback_log.append(f"[{step}] {message}")
