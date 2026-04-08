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
from app.services.swarm_observability import finalize_swarm_trace, record_swarm_triage, start_swarm_trace


class SwarmTaskDef(BaseModel):
    id: str = Field(description="Unique task ID, e.g., T1")
    agent_name: str = Field(description="Name of the agent to execute this task")
    instruction: str = Field(description="Highly detailed instruction for the agent")
    depends_on: list[str] = Field(default_factory=list, description="IDs of tasks that must complete before this one")


class SwarmPlan(BaseModel):
    tasks: list[SwarmTaskDef] = Field(default_factory=list)
    reasoning: str = Field(default="No explicit reasoning provided.")


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

    async def _plan(self, query: str, feedback_history: str = "", historical_context: str = "") -> SwarmPlan:
        """Analyze query and generate a DAG with mandatory Checkpoints and Cross-Review (M4.2.2)."""
        system_prompt = f"""
        You are the HVM-Supervisor, an expert in 'Recursive Multi-Agent Coordination'.
        Available agents: {self.available_agents}
        
        Mandatory Swarm Protocol:
        1.  CROSS-REVIEW: For any non-trivial Code or Research task, MANDATE a 'ReviewerAgent' task to critique the result.
        2.  VERIFICATION POINTS: Each instruction MUST include explicit success criteria (Checkpoints).
        3.  BLACKBOARD: Agents see previous context; use this to challenge assumptions.
        
        Workflow Requirements:
        - Research/Audit first.
        - Execution second.
        - Independent Audit/Critique third (Peer Review).
        
        ### LONG-TERM ARCHITECTURE CONTEXT
        {historical_context}
        
        Previous feedback (if replan):
        {feedback_history}
        
        Output JSON:
        {{
          "reasoning": "Strategy for the dual-viewpoint review",
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
            tier=3,
            prompt=f"Objective: {query}",
            system_prompt=system_prompt,
            response_format={"type": "json_object"}
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

    async def _verify(self, query: str, context: dict[str, Any]) -> VerifyResult:
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
            response_format={"type": "json_object"}
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
                if not agent:
                    shared_blackboard[task_id] = f"Error: Agent {task_def.agent_name} not found."
                    continue

                # 🧠 Swarm Advantage: Agents get DIRECT dependencies + FULL blackboard access
                dep_context = {dep: shared_blackboard.get(dep, "") for dep in task_def.depends_on}

                agent_task = AgentTask(
                    id=task_id,
                    swarm_trace_id=trace_id,
                    description=f"Part of: {query}",
                    instruction=task_def.instruction,
                    context=dep_context,
                    blackboard=shared_blackboard # The BIG difference: peer visibility
                )
                tasks_to_run.append((task_id, agent.execute(agent_task)))

            if tasks_to_run:
                # Parallel await
                ids = [t[0] for t in tasks_to_run]
                coros = [t[1] for t in tasks_to_run]
                results = await asyncio.gather(*coros)

                for task_id, res in zip(ids, results, strict=False):
                    shared_blackboard[task_id] = res.output

                    # 💡 React to Intelligence Signals from the Swarm (M4.2.2)
                    if res.signal:
                        logger.info(f"⚡ Received Signal from {task_id}: {res.signal}")

                        # 🦾 Cross-Viewpoint Reactivity:
                        # If a Reviewer signals a critical failure, stop the DAG and trigger REPLAN
                        if res.signal.get("requires_replan") or res.signal.get("critical_failure"):
                            logger.error(f"🚨 [Swarm Critique] {task_id} reported a blocker! Forcing Re-plan.")
                            # Store the review as part of the context and exit early
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

    async def run_swarm(self, query: str, user_id: str | None = None, conversation_id: str | None = None) -> dict[str, Any]:
        """Execute the Cognitive Loop: Plan -> Execute -> Verify -> Replans."""
        effective_user_id = user_id or self.user_id
        trace_id = await start_swarm_trace(query, user_id=effective_user_id)

        loop_count = 0
        feedback_history = ""
        final_context = {}

        # 🧠 PHASE 0: Context Hydration
        historical_context = await self.memory_bridge.load_historical_context(query)

        try:
            while loop_count < self.max_loops:
                loop_count += 1
                logger.info(f"--- SWARM LOOP {loop_count}/{self.max_loops} ---")

                # 1. PLAN
                plan = await self._plan(query, feedback_history, historical_context)
                await record_swarm_triage(trace_id, f"Loop {loop_count} Plan: {plan.reasoning}")
                logger.info(f"Plan generated with {len(plan.tasks)} tasks.")

                if not plan.tasks:
                    logger.warning("Empty plan generated.")
                    break

                # 2. EXECUTE (DAG)
                final_context = await self._execute_dag(plan, trace_id, query)

                # 3. VERIFY
                verify_res = await self._verify(query, final_context)
                logger.info(f"Verification Result: Complete={verify_res.is_complete}, Feedback={verify_res.feedback}")

                if verify_res.is_complete:
                    logger.info("Swarm objective achieved!")
                    # 📼 PHASE 4: Memory Persistence (Success)
                    await self.memory_bridge.persist_successful_outcome(
                        query, final_context, conversation_id=conversation_id
                    )
                    break
                else:
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

