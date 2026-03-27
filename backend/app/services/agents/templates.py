from typing import List, Dict, Any
from pydantic import BaseModel

class VerificationPoint(BaseModel):
    name: str # e.g. "Security Audit"
    description: str # e.g. "Check for hardcoded secrets"
    success_criteria: List[str]

# Standard Swarm Checkpoint Templates
SWARM_TEMPLATES = {
    "code_generation": [
        VerificationPoint(
            name="Logic Correctness",
            description="Functional alignment with objective",
            success_criteria=["No obvious logical loops", "All edge cases mentioned handled"]
        ),
        VerificationPoint(
            name="Security Standard (M1.2)",
            description="PII, Credentials, Escaping",
            success_criteria=["No unmasked PII", "No hardcoded credentials"]
        )
    ],
    "research": [
        VerificationPoint(
            name="Source Reliability",
            description="Check for hallucinations/contradictions",
            success_criteria=["No internal contradictions found", "Sources cited correctly"]
        )
    ]
}

def get_checkpoints_for_task(task_type: str) -> List[VerificationPoint]:
    return SWARM_TEMPLATES.get(task_type, [])
