
from typing import Any, List, Dict
from pydantic import BaseModel, Field
from loguru import logger
from app.services.llm_gateway import llm_gateway

class ScopingResult(BaseModel):
    is_clear: bool
    priority: int = Field(ge=1, le=5, description="1: Trivial, 5: Mission Critical")
    priority_reasoning: str
    missing_dimensions: List[str]
    critical_questions: List[str]
    suggested_defaults: Dict[str, str]

class ScopingAgent:
    """
    L5 Strategy: Prevents 'blind discussion' by auditing requirement clarity first.
    """
    async def audit_query(self, query: str) -> ScopingResult:
        logger.info(f"🧐 [Scoping] Auditing requirement clarity for: {query}")
        
        prompt = f"""
        Analyze this engineering requirement for ambiguity and importance. 
        Identify if critical dimensions are missing: 
        1. Scale (RPS, users)
        2. Technical Stack constraints
        3. Security/Regulatory level
        4. Budget/Cost constraints
        
        QUERY: {query}
        
        ASSIGN A PRIORITY (1-5):
        1: Routine maintenance, simple fixes, no architectural impact.
        2: Feature addition with local impact.
        3: Significant feature or minor architectural shift.
        4: Core architectural change, security-sensitive, or high-scale.
        5: Mission critical, wide-reaching impact, high risk of failure.
        
        Return a JSON object with:
        - is_clear: boolean (true if all 4 dimensions are present or inferable)
        - priority: integer 1-5
        - priority_reasoning: why did you assign this level?
        - missing_dimensions: list of strings
        - critical_questions: top 3 questions to ask the human.
        - suggested_defaults: your best industrial guess.
        """
        
        try:
            response = await llm_gateway.call_tier(
                tier=2, # Fast analysis
                prompt=prompt,
                system_prompt="You are a Requirement Auditor focused on precision and engineering pragmatism.",
                response_format={"type": "json_object"}
            )
            
            import json
            data = json.loads(response.content)
            return ScopingResult(**data)
        except Exception as e:
            logger.error(f"❌ [Scoping] Audit failed: {e}. Falling back to default Priority 2.")
            return ScopingResult(
                is_clear=False,
                priority=2,
                priority_reasoning="Fallback due to audit system error.",
                missing_dimensions=["Generic Scale", "Tech Stack"],
                critical_questions=["Could you please provide more detail on the scale and tech constraints?"],
                suggested_defaults={"scale": "Medium", "stack": "Standard Python/React"}
            )
