
from typing import Any, List, Dict
from pydantic import BaseModel
from loguru import logger
from app.services.llm_gateway import llm_gateway

class ScopingResult(BaseModel):
    is_clear: bool
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
        Analyze this engineering requirement for ambiguity. 
        Identify if critical dimensions are missing: 
        1. Scale (RPS, users)
        2. Technical Stack constraints
        3. Security/Regulatory level
        4. Budget/Cost constraints
        
        QUERY: {query}
        
        Return a JSON object with:
        - is_clear: boolean (true if all 4 are present or inferable with high confidence)
        - missing_dimensions: list of strings
        - critical_questions: top 3 questions to ask the human before starting ANY work.
        - suggested_defaults: if you had to guess, what would be the standard industry defaults?
        """
        
        response = await llm_gateway.call_tier(
            tier=2, # Fast analysis
            prompt=prompt,
            system_prompt="You are a Requirement Auditor focused on precision and engineering pragmatism.",
            response_format={"type": "json_object"}
        )
        
        import json
        data = json.loads(response.content)
        return ScopingResult(**data)
