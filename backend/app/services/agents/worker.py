"""
HiveMind Worker Base Class (M4.1.2 + M8.0.1 Harness Integration)

Standardizes the agent lifecycle:
1. init:      Context setup.
2. execute:   Run the task.
3. harness:   Computational + Policy checks (M8).
4. reflect:   Check if goals were met (Inferential).
"""

import asyncio
from typing import Any

from loguru import logger

from app.services.agents.protocol import AgentResponse, AgentStatus, AgentTask, BaseAgent
from app.services.llm_gateway import llm_gateway
from app.prompts.dialect import model_dialect
from app.services.agents.review_governance import review_governance


def _infer_output_type(agent_name: str, content: str) -> str:
    """根据 Agent 名称和输出内容推断输出类型。"""
    if "Code" in agent_name:
        return "code"
    if "Reviewer" in agent_name:
        return "json"
    if "```python" in content or "```py" in content:
        return "code"
    if content.strip().startswith("{") or content.strip().startswith("["):
        return "json"
    return "text"


class WorkerAgent(BaseAgent):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Main entry for Agent execution with Harness + Tracing (M4.1.4 + M8.0.1)."""
        import time

        from app.models.observability import TraceStatus as ObsStatus
        from app.services.swarm_observability import record_swarm_span

        start_time = time.time()
        self.status = AgentStatus.EXECUTING
        logger.info(f"Agent {self.name} executing task: {task.id}")

        # 🏎️ L5 Adaptation: Apply Model-Specific Dialect to the instruction
        priority = task.context.get("priority", 2)
        target_model_profile = review_governance.get_optimal_critic(priority)
        target_model = target_model_profile.name.lower().replace(" ", "-")

        task.instruction = model_dialect.wrap_instruction(target_model, task.instruction)

        try:
            # 🛡️ M8.3.1 + Prompt Assembler: 三层 Prompt 组装（KV Cache 优化）
            # Layer 1+2 → system_prompt（缓存友好），Layer 3 → 已在 task.instruction 中
            try:
                from app.sdk.harness.prompt_assembler import build_static_shell, build_warm_context

                cached_shell = await build_static_shell(self.name)
                cached_warm = await build_warm_context(self.name)
                # 将 Layer 1+2 的约束注入到 task context 中，供 _run_logic 使用
                if cached_shell or cached_warm:
                    task.context["_harness_system_prefix"] = (cached_shell + "\n" + cached_warm).strip()
            except Exception as e:
                logger.debug(f"Prompt assembler skipped: {e}")

            # 1. Logic Execution — Agent 生成输出
            output, knowledge, signal, memories = await self._run_logic(task)
            latency_ms = (time.time() - start_time) * 1000

            # 🛡️ 2. HARNESS CHECK (M8.0.1) — Computational + Policy 检查
            harness_result = await self._harness_check(task, str(output))

            # 如果 Harness 有 error 级别的失败，标记到 signal 中
            if not harness_result.passed:
                if signal is None:
                    signal = {}
                signal["harness_blocked"] = True
                signal["harness_errors"] = [e.message for e in harness_result.errors]
                logger.warning(
                    f"🛡️ Agent {self.name} output BLOCKED by Harness: "
                    f"{harness_result.summary}"
                )

            # 如果有 warnings，记录到 context 中（不阻断）
            if harness_result.warnings:
                task.context["harness_warnings"] = [
                    {"policy": w.policy_name, "message": w.message}
                    for w in harness_result.warnings
                ]

            # 3. Reflection (Inferential Feedback)
            self.status = AgentStatus.REFLECTING
            await self._reflect(task, output)

            self.status = AgentStatus.DONE

            # 🔒 4. RECORD TRACE
            if task.swarm_trace_id:
                asyncio.create_task(record_swarm_span(
                    trace_id=task.swarm_trace_id,
                    agent_name=self.name,
                    instruction=task.instruction,
                    output=str(output),
                    latency_ms=latency_ms,
                    status=ObsStatus.SUCCESS,
                    details={
                        "related_memories": memories or [],
                        "reasoning_budget": task.context.get("reasoning_budget"),
                        "model_variant": target_model,
                        # 🛡️ M8: Harness 检查结果写入 Trace
                        "harness_passed": harness_result.passed,
                        "harness_errors": len(harness_result.errors),
                        "harness_warnings": len(harness_result.warnings),
                        "harness_latency_ms": harness_result.total_latency_ms,
                    }
                ))

                # 🛡️ M8.1.3: Harness 检查结果写入图谱（fire-and-forget）
                if harness_result.errors or harness_result.warnings:
                    try:
                        from app.sdk.harness.graph_integration import record_harness_check

                        asyncio.create_task(record_harness_check(
                            trace_id=task.swarm_trace_id,
                            agent_name=self.name,
                            task_id=task.id,
                            passed=harness_result.passed,
                            errors=[{"policy_name": e.policy_name, "message": e.message, "level": e.level} for e in harness_result.errors],
                            warnings=[{"policy_name": w.policy_name, "message": w.message, "level": w.level} for w in harness_result.warnings],
                            total_latency_ms=harness_result.total_latency_ms,
                        ))
                    except Exception:
                        pass  # 图谱写入失败不影响主流程

            return AgentResponse(
                task_id=task.id,
                output=str(output),
                new_knowledge=knowledge or {},
                signal=signal or {},
                related_memories=memories or [],
                status=self.status
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.exception(f"Agent {self.name} FAILED: {e}")
            self.status = AgentStatus.FAILED

            if task.swarm_trace_id:
                asyncio.create_task(record_swarm_span(
                    trace_id=task.swarm_trace_id,
                    agent_name=self.name,
                    instruction=task.instruction,
                    output=f"Error: {e}",
                    latency_ms=latency_ms,
                    status=ObsStatus.FAILED
                ))

            return AgentResponse(task_id=task.id, output=f"Internal Error: {e}", status=self.status)

    async def _harness_check(self, task: AgentTask, output: str) -> Any:
        """
        🛡️ M8.0.1: 对 Agent 输出执行 Harness 检查。

        调用 HarnessEngine.check_agent_output()，传入 Agent 上下文。
        失败时不抛异常，而是返回 HarnessResult 供调用方决策。
        """
        try:
            from app.sdk.harness.engine import get_harness_engine

            engine = get_harness_engine()
            output_type = _infer_output_type(self.name, output)

            result = await engine.check_agent_output(
                content=output,
                agent_name=self.name,
                task_id=task.id,
                task_instruction=task.instruction[:500],  # 截断避免过长
                output_type=output_type,
            )
            return result
        except Exception as exc:
            # Harness 自身崩溃不应阻断 Agent 执行
            logger.error(f"🛡️ Harness check failed for {self.name}: {exc}")
            # 返回一个"通过"的结果，降级处理
            from app.sdk.harness.policy import HarnessResult
            return HarnessResult(passed=True)

    async def _run_logic(self, task: AgentTask) -> tuple[Any, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        """Worker's specialized logic. Returns (Output, Knowledge, Signal, RelatedMemories)."""
        raise NotImplementedError("Subclasses must implement _run_logic.")

    async def _reflect(self, task: AgentTask, output: Any) -> None:
        """
        L5 Node-Level Reflection: Self-Correction phase using a fast model.
        Verifies if the output satisfies the original instruction checkpoints.
        """
        logger.debug(f"Agent {self.name} performing structured reflection on output...")

        reflection_prompt = f"""
        Review the following AI agent output against the given instruction.
        
        ### Instruction:
        {task.instruction}
        
        ### Output to Check:
        {str(output)[:2000]}
        
        Check if the output:
        1. Correctly follows the instruction logic.
        2. Maintains valid formatting (JSON/Code).
        3. Doesn't contain 'hallucinated' errors or placeholders.
        
        Return ONLY valid JSON:
        {{
          "is_valid": true | false,
          "reason": "summary of findings",
          "improvement_suggestion": "optional"
        }}
        """

        try:
            res = await llm_gateway.call_tier(
                tier=1,
                prompt=reflection_prompt,
                system_prompt="You are a node-level quality critic.",
                response_format={"type": "json_object"}
            )
            import json
            critique = json.loads(res.content)

            if not critique.get("is_valid", True):
                logger.warning(f"⚠️ Agent {self.name} node-reflection failed: {critique.get('reason')}")
                task.context["node_reflection_failure"] = critique.get("reason")
            else:
                logger.info(f"✅ Agent {self.name} node-reflection passed.")
        except Exception as e:
            logger.error(f"Node reflection error for {self.name}: {e}")
            pass
