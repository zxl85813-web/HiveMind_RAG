"""
Harness Service.
Executes and evaluates Draft Agents in the Sandbox.
"""
import time
import asyncio
from typing import List, Dict, Any
from loguru import logger
from pydantic import BaseModel

from app.models.builder import AgentConfig, SandboxSession
from app.services.evaluation.multi_grader import MultiGraderEval
from app.agents.swarm import SwarmOrchestrator, AgentDefinition
from app.skills.registry import get_skill_registry

class EvalResult(BaseModel):
    case_id: str
    question: str
    response: str
    expected: str
    score: float
    verdict: str
    reasoning: str
    latency_ms: float
    tokens_used: int
    tool_calls: List[str]

class HarnessService:
    def __init__(self):
        self.grader = MultiGraderEval()
        self.registry = get_skill_registry()

    async def run_evaluation(
        self, 
        agent_config: Dict[str, Any], 
        test_cases: List[Dict[str, Any]]
    ) -> List[EvalResult]:
        """
        Runs a full evaluation suite against a draft agent config.
        """
        logger.info(f"🧪 [Harness] Starting evaluation for {agent_config.get('name')}")
        
        # 1. Setup the "Draft Agent" in the Swarm
        # We simulate a specialized orchestrator for the draft
        swarm = SwarmOrchestrator()
        
        # Prepare tools from the config
        tools = []
        for tool_name in agent_config.get("tools", []):
            t = self.registry.get_tool(tool_name)
            if t:
                tools.append(t)
        
        # Define the draft agent
        draft_agent = AgentDefinition(
            name="DraftAgent",
            description="The agent being evaluated.",
            tools=tools,
            model_hint="balanced"
        )
        
        # Note: In a real swarm, we'd register this agent. 
        # For evaluation, we might just bypass the supervisor and call it directly.
        
        results = []
        
        for i, case in enumerate(test_cases):
            start_time = time.time()
            question = case.get("question", "")
            expected = case.get("expected_outcome", "")
            
            logger.info(f"  [Case {i+1}] Testing: {question[:50]}...")
            
            # 2. Execute the Agent
            # Here we wrap the system prompt into the context or a system message
            context = {
                "system_override": agent_config.get("system_prompt"),
                "is_eval_run": True
            }
            
            try:
                # We use a simplified swarm call for the draft
                # In production, this would use the real orchestrator logic
                response_data = await swarm.invoke(question, context)
                
                # Extract response and metrics
                full_response = response_data.get("messages", [])[-1].content if response_data.get("messages") else ""
                # Mock tokens for now
                tokens = len(full_response.split()) * 1.5 
                
                # 3. Grade the result
                grade = await self.grader.evaluate(question, full_response, context=expected)
                
                latency = (time.time() - start_time) * 1000
                
                results.append(EvalResult(
                    case_id=str(i),
                    question=question,
                    response=full_response,
                    expected=expected,
                    score=grade.composite_score,
                    verdict=grade.verdict,
                    reasoning=grade.summary,
                    latency_ms=latency,
                    tokens_used=int(tokens),
                    tool_calls=[m.get("tool_name") for m in response_data.get("messages", []) if m.get("tool_name")]
                ))
                
            except Exception as e:
                logger.error(f"  [Case {i+1}] Execution failed: {e}")
                results.append(EvalResult(
                    case_id=str(i),
                    question=question,
                    response=f"Error: {str(e)}",
                    expected=expected,
                    score=0.0,
                    verdict="FAIL",
                    reasoning=f"Runtime error: {str(e)}",
                    latency_ms=0,
                    tokens_used=0,
                    tool_calls=[]
                ))
        
        return results

    async def create_sandbox_session(
        self, 
        session_id: str, 
        agent_config_id: str, 
        results: List[EvalResult]
    ) -> str:
        """
        Persists the results to a SandboxSession.
        """
        # Logic to save to DB (SQLModel)
        # sandbox = SandboxSession(
        #     builder_session_id=session_id,
        #     agent_config_id=agent_config_id,
        #     input_payload=json.dumps([r.dict() for r in results]),
        #     ...
        # )
        return "sandbox_id_123"
