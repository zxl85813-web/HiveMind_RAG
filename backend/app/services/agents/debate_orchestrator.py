
import asyncio
from typing import Any, List
from loguru import logger
from pydantic import BaseModel
from app.services.agents.supervisor import SupervisorAgent
from app.services.llm_gateway import llm_gateway

from app.services.agents.workers.scoping_agent import ScopingAgent
from app.services.agents.skill_factory import skill_factory

class DebateResult(BaseModel):
    scoping_audit: Any | None = None
    proposal_a: dict[str, Any]
    proposal_b: dict[str, Any]
    critique_a_by_b: str
    critique_b_by_a: str
    consensus_plan: str
    winner_score_a: float
    winner_score_b: float

class DebateOrchestrator:
    """
    L5 Synergy: Orchestrates multiple Swarms to debate complex architectural decisions.
    """
    def __init__(self, agents_pool: List[Any]):
        self.swarm_a = SupervisorAgent(agents=agents_pool, user_id="swarm_a_performance")
        self.swarm_b = SupervisorAgent(agents=agents_pool, user_id="swarm_b_security")
        self.scoping_gate = ScopingAgent()

    async def run_debate(self, query: str, max_rounds: int = 2, human_steer: str | None = None) -> DebateResult:
        logger.info(f"⚔️ [L5 Debate] Starting Inter-Swarm Debate for: {query}")
        
        # 🕵️ L5 SCOPING GATE: Clarify BEFORE Discussing + Determine Priority
        audit = await self.scoping_gate.audit_query(query)
        
        # 🚦 L5 PRIORITY STRATEGY
        priority = audit.priority or 2
        logger.info(f"🚦 [L5 Priority] Assigned Level: {priority} ({audit.priority_reasoning})")
        
        # Mapping Priority to Strategy
        # Models can be overridden here if configured in settings, for now we use tiers but could inject specific strings
        strategy = {
            1: {"rounds": 1, "tier": 1, "use_diversity": False},
            2: {"rounds": 2, "tier": 2, "use_diversity": False},
            3: {"rounds": 3, "tier": 3, "use_diversity": False},
            4: {"rounds": 4, "tier": 3, "use_diversity": True, "model_a": "gpt-4o", "model_b": "claude-3-opus-20240229"},
            5: {"rounds": 5, "tier": 3, "use_diversity": True, "model_a": "gpt-4-turbo", "model_b": "gemini-1.5-pro"}
        }.get(priority, {"rounds": 2, "tier": 2, "use_diversity": False})

        rounds = strategy["rounds"]
        tier = strategy["tier"]
        model_a = strategy.get("model_a") if strategy["use_diversity"] else None
        model_b = strategy.get("model_b") if strategy["use_diversity"] else None

        if not audit.is_clear:
            logger.warning(f"⚠️ [SCOPING ALERT] Blind discussion detected! Missing: {audit.missing_dimensions}")
            logger.warning(f"👉 MUST CLARIFY: {audit.critical_questions}")
        
        # ⚓ STRATEGIC ANCHOR: The 'Moderator' voice + Human Steer
        steer_prefix = f"### 👑 HUMAN STEER: {human_steer}\n" if human_steer else ""
        moderator_voice = f"{steer_prefix}MODERATOR NOTICE: Stay focused on the ORIGINAL QUERY: '{query}'. Importance Tier: {priority}. Avoid pedantic depth. Focus on actionable architecture."

        # 1. Generate parallel proposals (PHASE 1)
        logger.info(f"PHASE 1: Generating competing proposals (Strategy: Tier {tier}, Diverse: {strategy['use_diversity']})...")
        task_a = self.swarm_a.run_swarm(f"{moderator_voice}\nPROPOSE A PERFORMANCE-FIRST SOLUTION.", human_steer=human_steer, model_override=model_a, priority_override=priority)
        task_b = self.swarm_b.run_swarm(f"{moderator_voice}\nPROPOSE A SECURITY-FIRST SOLUTION.", human_steer=human_steer, model_override=model_b, priority_override=priority)
        
        results = await asyncio.gather(task_a, task_b)
        res_a, res_b = results[0], results[1]

        # 2. Iterative Critique with Round Cap
        logger.info(f"PHASE 2: Iterative Cross-Critique (Max {rounds} rounds)...")
        current_a = res_a
        current_b = res_b
        
        last_critique_a = "No critique yet."
        last_critique_b = "No critique yet."

        for r in range(rounds):
            logger.info(f"--- Debate Round {r+1}/{rounds} ---")
            
            # Cross-Critique (Swarm B critiques A, Swarm A critiques B)
            critique_a = await self.swarm_b.run_swarm(f"{moderator_voice}\nCRITIQUE PROPOSAL A based on Security Standards: {current_a}", human_steer=human_steer, model_override=model_b, priority_override=priority)
            critique_b = await self.swarm_a.run_swarm(f"{moderator_voice}\nCRITIQUE PROPOSAL B based on Performance Metrics: {current_b}", human_steer=human_steer, model_override=model_a, priority_override=priority)
            
            # Just keep the last critiques for synthesis
            last_critique_a = critique_a
            last_critique_b = critique_b

        # 3. Final Synthesis (PHASE 3: Forced Convergence)
        logger.info("PHASE 3: Forced Convergence by HVM-Synthesizer...")
        synthesis_prompt = f"""
        You are the HVM-Synthesizer. You must resolve a high-level architectural debate.
        
        OBJECTIVE PRIORITY: {priority} ({audit.priority_reasoning})
        QUERY: {query}
        
        SWARM A (PERFORMANCE) PROPOSAL: {res_a}
        LAST CRITIQUE BY SWARM B: {last_critique_a}
        
        SWARM B (SECURITY) PROPOSAL: {res_b}
        LAST CRITIQUE BY SWARM A: {last_critique_b}
        
        Produce a final synthesized plan that merges the strengths of both and addresses all critiques.
        IMPORTANT: Penalize (lower score) any swarm that drifted into irrelevant pedantic depth or ignored the original query.
        Assign a score (0.0-1.0) to both initial proposals based on their contribution and STRATEGIC ALIGNMENT.
        """
        
        response = await llm_gateway.call_tier(
            tier=3, # High reasoning for synthesis
            prompt=synthesis_prompt,
            system_prompt="You are a Master Architect focused on finding the 'Golden Path'.",
            response_format={"type": "json_object"}
        )
        
        import json
        data = json.loads(response.content)
        
        # 🏛️ L5 SOLIDIFICATION: Persistent Collective Wisdom
        await self.swarm_a.memory_bridge.solidify_swarm_consensus(
            query=query,
            consensus_plan=data.get("consensus_plan", ""),
            rationale=data.get("why_this_is_best", "Synthesized from multi-swarm debate."),
            trace_id=res_a.get("final_context", {}).get("trace_id", "L5-DEBATE")
        )

        # 🏗️ L5 SKILL SYNTHESIS: Industrialize Output (Autonomous Skill Factory)
        if len(data.get("consensus_plan", "")) > 100:
            await skill_factory.synthesize_skill(
                task_name=query,
                code_content=data.get("consensus_plan", ""),
                description=data.get("why_this_is_best", "Autonomous synthesis from HiveMind Swarm.")
            )

        return DebateResult(
            scoping_audit=audit,
            proposal_a=res_a,
            proposal_b=res_b,
            critique_a_by_b=str(last_critique_a),
            critique_b_by_a=str(last_critique_b),
            consensus_plan=data.get("consensus_plan", ""),
            winner_score_a=data.get("score_a", 0.5),
            winner_score_b=data.get("score_b", 0.5)
        )
