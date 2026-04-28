"""
HiveMind Supervisor (M4.2.0) - Cognitive Loop Architecture

Implements the Research -> Plan -> Execute -> Verify -> Loop pattern.
Supports Dynamic Task DAG and Context Passing between agents.
"""

import asyncio
from typing import Any

import networkx as nx
from loguru import logger
from pydantic import BaseModel, Field

from app.models.observability import TraceStatus as ObsStatus
from app.services.agents.memory_bridge import SwarmMemoryBridge
from app.services.agents.protocol import AgentTask
from app.services.llm_gateway import llm_gateway
from app.llm.guardrails import check_input
from app.services.swarm_observability import finalize_swarm_trace, record_swarm_triage, start_swarm_trace


class SwarmTaskDef(BaseModel):
    id: str = Field(description="Unique task ID, e.g., T1")
    agent_name: str = Field(description="Name of the agent to execute this task")
    instruction: str = Field(description="Highly detailed instruction for the agent")
    depends_on: list[str] = Field(default_factory=list, description="IDs of tasks that must complete before this one")


class SwarmPlan(BaseModel):
    tasks: list[SwarmTaskDef] = Field(default_factory=list)
    reasoning: str = Field(default="No explicit reasoning provided.")
    directive_compliance: Any = Field(default="N/A", description="How the plan adheres to L4 System Directives")


class VerifyResult(BaseModel):
    is_complete: bool = Field(description="True if the final goal is met, False otherwise")
    feedback: str = Field(description="If incomplete, detailed explanation of what is missing or wrong to feed into the next loop")


class SupervisorAgent:
    def __init__(self, agents: list[Any], user_id: str = "system-default", max_loops: int = 3):
        self.name = "HVM-Supervisor"
        self.user_id = user_id
        self.agents = {a.name: a for a in agents}
        self.available_agents = [
            {"name": a.name, "description": a.description} for a in agents
        ]
        self.max_loops = max_loops
        # 🧠 Memory integration (M4.2.1)
        self.memory_bridge = SwarmMemoryBridge(user_id=user_id)

    async def _plan(self, query: str, feedback_history: str = "", historical_context: str = "", is_high_risk: bool = False, human_steer: str | None = None, model_override: str | None = None) -> SwarmPlan:
        """Analyze query and generate a DAG with mandatory Checkpoints and Cross-Review (M4.2.2)."""
        
        # 🛡️ L4/L5 Strategic Governance
        risk_guidance = ""
        target_tier = 3
        if is_high_risk:
            risk_guidance = "### 🚨 HIGH COGNITIVE RISK DETECTED: Use MAXIMALLY conservative planning."

        # 👑 L5 Human Strategic Steering (HAT)
        steer_guidance = ""
        if human_steer:
            steer_guidance = f"### 👑 HUMAN COMMANDER INTERVENTION: {human_steer}\nThis is your ABSOLUTE priority. Stop any diverging research and follow this direction NOW."

        # 🛡️ M8.3.2: Harness Feedforward — 从缓存加载全局约束（KV Cache 优化）
        harness_constraints = ""
        try:
            from app.sdk.harness.prompt_assembler import build_static_shell, build_warm_context

            # 复用 Redis 缓存的 Layer 1+2，避免每次查图谱
            shell = await build_static_shell("HVM-Supervisor")
            warm = await build_warm_context("HVM-Supervisor")
            if shell or warm:
                harness_constraints = (shell + "\n" + warm).strip()
        except Exception:
            pass  # 缓存/图谱不可用时静默降级

        system_prompt = f"""
        You are the HVM-Supervisor, an expert in 'Recursive Multi-Agent Coordination'.
        
        {steer_guidance}
        {risk_guidance}
        {harness_constraints}
        
        ### CONSTITUTIONAL GOVERNANCE (L4)
        Reference: docs/governance/L4_GOVERNANCE_STATUTES.md
        All plans MUST comply with the 3 Iron Rules:
        1. Mandatory Adversarial Review
        2. Strict Evidence Lineage
        3. Cognitive Honesty Declaration
        
        {risk_guidance}
        
        Available agents: {self.available_agents}
        2.  VERIFICATION POINTS: Each instruction MUST include explicit success criteria (Checkpoints).
        3.  BLACKBOARD: Agents see previous context; use this to challenge assumptions.
        
        ### MANDATORY EVOLUTIONARY CONSTRAINTS (L4)
        The following directives are derived from PAST FAILURES. 
        FAILURE TO ADHERE TO THESE WILL TRIGGER AN L4 INTEGRITY REJECTION:
        {historical_context}
        
        Workflow Requirements:
        
        Previous feedback (if replan):
        {feedback_history}
        
        Output JSON:
        {{
          "reasoning": "Strategy for the dual-viewpoint review",
          "directive_compliance": "Explicitly state which SYSTEM DIRECTIVES from context were applied",
          "tasks": [
            {{
              "id": "t1",
              "agent_name": "ResearchAgent",
              "instruction": "Find X. [Checkpoint: No factual contradictions]",
              "depends_on": []
            }},
            {{
              "id": "t2",
              "agent_name": "ReviewerAgent",
              "instruction": "Critique T1's findings from a security perspective.",
              "depends_on": ["t1"]
            }}
          ]
        }}
        """
        response = await llm_gateway.call_tier(
            tier=target_tier,
            prompt=f"Objective: {query}",
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
            model_override=model_override
        )

        import json
        try:
            data = json.loads(response.content)
            plan = SwarmPlan(**data)

            # ====================================================================
            # 🔒 POLICY ENFORCEMENT: Hard-inject HVM-Reviewer (Code-level guarantee)
            # We NEVER rely on the LLM to self-police this rule.
            # For any plan with more than 1 task, we inject a final audit pass.
            # ====================================================================
            has_reviewer = any(t.agent_name == "HVM-Reviewer" for t in plan.tasks)
            if len(plan.tasks) > 1 and not has_reviewer:
                all_ids = [t.id for t in plan.tasks]
                injected_reviewer = SwarmTaskDef(
                    id="t-audit",
                    agent_name="HVM-Reviewer",
                    instruction=(
                        f"[AUTO-INJECTED AUDIT] Perform a full cross-viewpoint critique "
                        f"of ALL task outputs for the objective: '{query}'. "
                        "Identify logic gaps, missing edge cases, and any security risks. "
                        "[Checkpoint: Must rate overall risk as Low/Medium/High and list specific concerns.]"
                    ),
                    depends_on=all_ids,  # Depends on ALL tasks → always runs last
                )
                plan.tasks.append(injected_reviewer)
                logger.info(
                    f"🛡️ [Policy Enforcement] HVM-Reviewer injected as 't-audit' "
                    f"(depends on: {all_ids})"
                )

            return plan
        except Exception as e:
            logger.error(f"Failed to parse Plan: {e}")
            return SwarmPlan(reasoning=f"Error: {e}")

    async def _verify(self, query: str, context: dict[str, Any], model_override: str | None = None) -> VerifyResult:
        """Reflect on the swarm's collective output to determine if the goal is met."""
        system_prompt = f"""
        You are the HVM-Reviewer.
        Original Objective: {query}
        
        Evaluate the collective outputs of the swarm's agents provided below.
        Did they achieve the objective fully and correctly?
        If not, what needs to be fixed or researched further?
        
        Output JSON:
        {{
          "is_complete": boolean,
          "feedback": "string explaining what is good and what is missing"
        }}
        """

        # Format the context for the reviewer
        context_str = "\n".join([f"=== Task {k} Output ===\n{v}" for k, v in context.items()])

        response = await llm_gateway.call_tier(
            tier=3,
            prompt=f"Swarm Outputs:\n{context_str}",
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
            model_override=model_override
        )

        import json
        try:
            data = json.loads(response.content)
            return VerifyResult(**data)
        except Exception as e:
            logger.error(f"Failed to parse Verification: {e}")
            return VerifyResult(is_complete=False, feedback="Verification parsing failed.")

    async def _execute_dag(self, plan: SwarmPlan, trace_id: str, query: str) -> dict[str, str]:
        """Execute a plan topologically, passing context through a HiveMind Blackboard."""
        G = nx.DiGraph()
        for task in plan.tasks:
            G.add_node(task.id, data=task)
            for dep in task.depends_on:
                G.add_edge(dep, task.id)

        if not nx.is_directed_acyclic_graph(G):
            raise ValueError("Plan is not a valid DAG (Cycle detected)")

        execution_order = list(nx.topological_sort(G))
        shared_blackboard = {}  # task_id -> output. This is the "Collective Brain".

        for batch in self._get_parallel_batches(G, execution_order):
            # Execute batch in parallel
            tasks_to_run = []
            for task_id in batch:
                task_def = G.nodes[task_id]['data']
                agent = self.agents.get(task_def.agent_name)
                
                # 🛡️ Agent Discovery Hardening
                if not agent:
                    err_msg = f"CRITICAL: Agent {task_def.agent_name} not found in current Swarm."
                    logger.error(err_msg)
                    shared_blackboard[task_id] = err_msg
                    # Ensure we record the failure in observability
                    continue

                # 🛡️ Dependency Gating: Skip if any parent failed
                deps_failed = [d for d in task_def.depends_on if "ERROR:" in str(shared_blackboard.get(d, ""))]
                if deps_failed:
                    msg = f"SKIPPED: Dependency failure on tasks: {deps_failed}"
                    logger.warning(f"⏩ {task_id} {msg}")
                    shared_blackboard[task_id] = msg
                    continue

                # 🧠 Swarm Advantage: Agents get DIRECT dependencies + FULL blackboard access
                dep_context = {dep: shared_blackboard.get(dep, "") for dep in task_def.depends_on}

                agent_task = AgentTask(
                    id=task_id,
                    swarm_trace_id=trace_id,
                    description=f"Part of: {query}",
                    instruction=task_def.instruction,
                    context={**dep_context, "priority": shared_blackboard.get("__priority__", 2)},
                    blackboard=shared_blackboard # The BIG difference: peer visibility
                )
                tasks_to_run.append((task_id, agent.execute(agent_task)))

            if tasks_to_run:
                ids = [t[0] for t in tasks_to_run]
                coros = [t[1] for t in tasks_to_run]
                
                # 🚀 L4 Hardened Parallel Execution: Isolation of failures
                results = await asyncio.gather(*coros, return_exceptions=True)

                for task_id, res in zip(ids, results, strict=False):
                    if isinstance(res, Exception):
                        logger.error(f"❌ [Swarm Fault] Task {task_id} crashed: {res}")
                        shared_blackboard[task_id] = f"ERROR: Execution failure: {str(res)}"
                        continue

                    shared_blackboard[task_id] = res.output

                    # 💡 Intelligence Signaling (M4.2.2)
                    if res.signal:
                        if res.signal.get("requires_replan") or res.signal.get("critical_failure"):
                            logger.error(f"🚨 [Swarm Critique] {task_id} reported a blocker! Forcing Re-plan.")
                            return shared_blackboard

        return shared_blackboard

    def _get_parallel_batches(self, G, topological_order):
        """Helper to group tasks that can be run in parallel."""
        batches = []
        G_copy = G.copy()
        while G_copy.nodes:
            zero_in_degree = [n for n, d in G_copy.in_degree() if d == 0]
            if not zero_in_degree:
                break
            batches.append(zero_in_degree)
            G_copy.remove_nodes_from(zero_in_degree)
        return batches

    async def run_swarm(self, query: str, user_id: str | None = None, conversation_id: str | None = None, human_steer: str | None = None, model_override: str | None = None, priority_override: int | None = None) -> dict[str, Any]:
        """Execute the Cognitive Loop: Plan -> Execute -> Verify -> Replans."""
        # 🛡️ P1 Guardrail: Verify input safety before planning
        guard = check_input(query)
        if not guard.safe:
            logger.error(f"🚨 Swarm rejected due to safety risk: {guard.matched_rules}")
            return {"status": "failed", "error": "Safety violation detected in query.", "risk_level": guard.risk_level}

        effective_user_id = user_id or self.user_id
        trace_id = await start_swarm_trace(query, user_id=effective_user_id)

        loop_count = 0
        feedback_history = ""
        final_context = {"__priority__": priority_override or 2} # Default or override priority

        # 🧠 PHASE 0: Context Hydration
        historical_context, is_high_risk = await self.memory_bridge.load_historical_context(query)

        try:
            while loop_count < self.max_loops:
                loop_count += 1
                logger.info(f"--- SWARM LOOP {loop_count}/{self.max_loops} ---")
                if is_high_risk:
                     logger.warning("⚠️ [L4 Cognitive Escalation] Planning with High-Risk context.")

                # 1. PLAN
                plan = await self._plan(query, feedback_history, historical_context, is_high_risk, human_steer=human_steer, model_override=model_override)
                await record_swarm_triage(trace_id, f"Loop {loop_count} Plan: {plan.reasoning}")
                logger.info(f"Plan generated with {len(plan.tasks)} tasks.")

                if not plan.tasks:
                    logger.warning("Empty plan generated.")
                    break

                # 2. EXECUTE (DAG)
                final_context = await self._execute_dag(plan, trace_id, query)

                # 🧠 L4 SENSORY: Cognitive Blocker Detection (M4.2.3)
                # Check if the process is moving or just 'spinning wheels'
                all_empty = all("No relevant information found" in str(v) for v in final_context.values())
                if all_empty and len(final_context) > 0:
                    logger.error("🚨 [L4 Circuit Breaker] Detection: Total Knowledge Vacuum. Halting.")
                    await self.memory_bridge.record_failure_reflection(query, "COGNITIVE_BLOCKER: Knowledge base returned nothing across all tasks.")
                    break

                # 3. VERIFY
                verify_res = await self._verify(query, final_context, model_override=model_override)
                logger.info(f"Verification Result: Complete={verify_res.is_complete}, Feedback={verify_res.feedback}")

                if verify_res.is_complete:
                    logger.info("Swarm objective achieved!")
                    # 📼 PHASE 4: Memory Persistence (Success)
                    await self.memory_bridge.persist_successful_outcome(
                        query, final_context, conversation_id=conversation_id
                    )
                    break
                else:
                    # 🔍 L4 SENSORY: Stagnation Detection
                    if verify_res.feedback in feedback_history:
                        logger.error("🚨 [L4 Circuit Breaker] Detection: Logical Stagnation. Re-plan is failing to address gaps. Halting.")
                        break

                    logger.warning("Objective incomplete. Preparing for replan...")
                    feedback_history += f"\nLoop {loop_count} Feedback: {verify_res.feedback}"
                    # 🪞 Record Reflection Gap
                    await self.memory_bridge.record_failure_reflection(query, verify_res.feedback)

            await finalize_swarm_trace(trace_id, status=ObsStatus.SUCCESS)
            return {
                "success": loop_count <= self.max_loops and (verify_res.is_complete if 'verify_res' in locals() else False),
                "loops_used": loop_count,
                "final_context": final_context,
                "feedback": verify_res.feedback if 'verify_res' in locals() else "Unknown"
            }

        except Exception as e:
            logger.exception(f"Swarm Workflow FAILED: {e}")
            await finalize_swarm_trace(trace_id, status=ObsStatus.FAILED)
            return {"success": False, "error": str(e)}

