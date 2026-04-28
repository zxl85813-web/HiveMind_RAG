"""
Harness Graph Integration — M8.1.2 / M9.1.1
=============================================
将 Harness 检查结果和策略写入 Neo4j 图谱。

核心功能:
  1. CognitiveDirective → HarnessPolicy 自动转化 (M9.1.1)
  2. HarnessCheck 结果写入图谱 (M8.1.3, 预留接口)
  3. 从图谱加载 Agent 绑定的策略 (M8.1.2, 预留接口)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger


async def directive_to_harness_policy(
    *,
    directive_id: str,
    topic: str,
    directive_text: str,
    confidence: float = 0.0,
) -> bool:
    """
    M9.1.1: 将 CognitiveDirective 转化为 HarnessPolicy 图谱节点。

    在 Neo4j 中创建:
      (:HarnessPolicy {id, name, type, directive, ...})
      (:CognitiveDirective)-[:SPAWNED]->(:HarnessPolicy)

    如果该 directive 已经有对应的 HarnessPolicy，则更新而非重复创建。

    Returns:
        True if successfully written to graph, False otherwise.
    """
    try:
        from app.sdk.core.graph_store import get_graph_store

        store = get_graph_store()
        policy_id = f"HP:directive:{directive_id}"

        # MERGE: 幂等写入，已存在则更新
        cypher = """
        MERGE (hp:HarnessPolicy {id: $policy_id})
        ON CREATE SET
            hp.name = $name,
            hp.type = 'feedforward',
            hp.agent_scope = 'all',
            hp.severity = CASE WHEN $confidence > 0.8 THEN 'error' ELSE 'warning' END,
            hp.directive = $directive,
            hp.source = 'cognitive_directive',
            hp.source_id = $directive_id,
            hp.is_active = true,
            hp.created_at = timestamp()
        ON MATCH SET
            hp.directive = $directive,
            hp.severity = CASE WHEN $confidence > 0.8 THEN 'error' ELSE 'warning' END,
            hp.updated_at = timestamp()
        WITH hp
        MERGE (cd:CognitiveDirectiveNode {id: $directive_id})
        ON CREATE SET cd.topic = $topic, cd.created_at = timestamp()
        MERGE (cd)-[:SPAWNED]->(hp)
        """

        await store.execute_query(cypher, {
            "policy_id": policy_id,
            "name": f"Directive: {topic}",
            "directive": directive_text[:500],
            "directive_id": directive_id,
            "topic": topic,
            "confidence": confidence,
        })

        logger.info(
            f"🛡️ [GraphIntegration] CognitiveDirective '{directive_id}' → "
            f"HarnessPolicy '{policy_id}' (topic: {topic})"
        )
        return True

    except Exception as exc:
        logger.warning(f"🛡️ [GraphIntegration] Failed to write HarnessPolicy to graph: {exc}")
        return False


async def record_harness_check(
    *,
    trace_id: str,
    agent_name: str,
    task_id: str,
    passed: bool,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    total_latency_ms: float,
) -> bool:
    """
    M8.1.3 (预留): 将 HarnessCheck 结果写入图谱。

    创建:
      (:HarnessCheck {id, passed, ...})
      (:SwarmSpan)-[:CHECKED_BY]->(:HarnessCheck)
      (:HarnessCheck)-[:ENFORCED_BY]->(:HarnessPolicy)

    当前为 fire-and-forget，不阻断主流程。
    """
    try:
        from app.sdk.core.graph_store import get_graph_store

        store = get_graph_store()
        check_id = f"HC:{uuid.uuid4().hex[:12]}"

        cypher = """
        CREATE (hc:HarnessCheck {
            id: $check_id,
            trace_id: $trace_id,
            agent_name: $agent_name,
            task_id: $task_id,
            passed: $passed,
            error_count: $error_count,
            warning_count: $warning_count,
            latency_ms: $latency_ms,
            created_at: timestamp()
        })
        """

        await store.execute_query(cypher, {
            "check_id": check_id,
            "trace_id": trace_id,
            "agent_name": agent_name,
            "task_id": task_id,
            "passed": passed,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "latency_ms": total_latency_ms,
        })

        # 关联到 SwarmSpan（如果存在）
        if trace_id:
            link_cypher = """
            MATCH (ss:SwarmSpan {trace_id: $trace_id, agent_name: $agent_name})
            MATCH (hc:HarnessCheck {id: $check_id})
            MERGE (ss)-[:CHECKED_BY]->(hc)
            """
            await store.execute_query(link_cypher, {
                "trace_id": trace_id,
                "agent_name": agent_name,
                "check_id": check_id,
            })

        # 关联到触发的 HarnessPolicy
        for err in errors + warnings:
            policy_name = err.get("policy_name", "")
            if policy_name:
                policy_cypher = """
                MATCH (hc:HarnessCheck {id: $check_id})
                MATCH (hp:HarnessPolicy) WHERE hp.name CONTAINS $policy_name
                MERGE (hc)-[:ENFORCED_BY]->(hp)
                """
                await store.execute_query(policy_cypher, {
                    "check_id": check_id,
                    "policy_name": policy_name,
                })

        return True

    except Exception as exc:
        logger.debug(f"🛡️ [GraphIntegration] HarnessCheck write skipped: {exc}")
        return False


# ── M8.2.3: Steering Loop ─────────────────────────────────────────────────────


async def run_steering_loop(window_hours: int = 24, failure_threshold: int = 5) -> dict[str, Any]:
    """
    M8.2.3: Steering Loop — 分析高频失败策略，自动生成新 Feedforward 规则。

    流程:
      1. 查询图谱：过去 window_hours 内 HarnessCheck.passed=false 的记录
      2. 按 policy 聚合，找出失败次数 > failure_threshold 的策略
      3. 从 CognitiveDirective 中提取相关教训
      4. 为高频失败的 Agent 生成新的 Feedforward HarnessPolicy 节点
      5. 建立 CognitiveDirective -[:SPAWNED]-> HarnessPolicy 边

    Returns:
        {
            "analyzed_checks": int,
            "high_frequency_failures": [...],
            "new_policies_created": int,
            "skipped": str | None,
        }
    """
    result: dict[str, Any] = {
        "analyzed_checks": 0,
        "high_frequency_failures": [],
        "new_policies_created": 0,
        "skipped": None,
    }

    try:
        from app.sdk.core.graph_store import get_graph_store

        store = get_graph_store()
        window_ms = window_hours * 3600 * 1000

        # 1. 查询高频失败策略
        cypher_failures = """
        MATCH (hc:HarnessCheck {passed: false})-[:ENFORCED_BY]->(hp:HarnessPolicy)
        WHERE hc.created_at > timestamp() - $window_ms
        WITH hp.name as policy_name, hp.id as policy_id,
             count(hc) as fail_count,
             collect(DISTINCT hc.agent_name) as affected_agents,
             collect(hc.task_id)[..5] as sample_tasks
        WHERE fail_count >= $threshold
        RETURN policy_name, policy_id, fail_count, affected_agents, sample_tasks
        ORDER BY fail_count DESC
        LIMIT 10
        """

        failures = await store.execute_query(cypher_failures, {
            "window_ms": window_ms,
            "threshold": failure_threshold,
        })

        if not failures:
            result["skipped"] = "No high-frequency failures found in the time window."
            logger.info(f"[SteeringLoop] No high-frequency failures in last {window_hours}h.")
            return result

        # 2. 统计总检查数
        count_result = await store.execute_query(
            "MATCH (hc:HarnessCheck) WHERE hc.created_at > timestamp() - $w RETURN count(hc) as total",
            {"w": window_ms},
        )
        result["analyzed_checks"] = count_result[0].get("total", 0) if count_result else 0

        # 3. 对每个高频失败策略，尝试从 CognitiveDirective 提取教训并生成新规则
        new_count = 0
        for failure in failures:
            policy_name = failure.get("policy_name", "")
            fail_count = failure.get("fail_count", 0)
            affected_agents = failure.get("affected_agents", [])

            result["high_frequency_failures"].append({
                "policy": policy_name,
                "fail_count": fail_count,
                "affected_agents": affected_agents,
            })

            # 查找相关的 CognitiveDirective
            directive_cypher = """
            MATCH (cd:CognitiveDirectiveNode)-[:SPAWNED]->(hp:HarnessPolicy)
            WHERE hp.name CONTAINS $keyword
            RETURN cd.id as directive_id, cd.topic as topic, hp.directive as directive
            LIMIT 3
            """
            # 用策略名的关键词搜索
            keyword = policy_name.split("/")[-1] if "/" in policy_name else policy_name
            directives = await store.execute_query(directive_cypher, {"keyword": keyword})

            if not directives:
                # 没有现有教训，创建一个新的 Feedforward 规则
                for agent in affected_agents:
                    new_policy_id = f"HP:steering:{agent}:{uuid.uuid4().hex[:8]}"
                    steering_cypher = """
                    MERGE (hp:HarnessPolicy {id: $pid})
                    SET hp.name = $name,
                        hp.type = 'feedforward',
                        hp.agent_scope = $agent,
                        hp.severity = 'warning',
                        hp.directive = $directive,
                        hp.source = 'steering_loop',
                        hp.is_active = true,
                        hp.created_at = timestamp(),
                        hp.fail_count_at_creation = $fail_count
                    """
                    await store.execute_query(steering_cypher, {
                        "pid": new_policy_id,
                        "name": f"Steering: {policy_name} for {agent}",
                        "agent": agent,
                        "directive": (
                            f"ATTENTION: The policy '{policy_name}' has failed {fail_count} times "
                            f"in the last {window_hours}h for agent '{agent}'. "
                            f"Review your output carefully to avoid triggering this policy."
                        ),
                        "fail_count": fail_count,
                    })

                    # 关联到原始策略
                    await store.execute_query(
                        "MATCH (new:HarnessPolicy {id: $new_id}), (old:HarnessPolicy {id: $old_id}) "
                        "MERGE (new)-[:DERIVED_FROM]->(old)",
                        {"new_id": new_policy_id, "old_id": failure.get("policy_id", "")},
                    )
                    new_count += 1

        result["new_policies_created"] = new_count

        # 🏗️ 缓存失效：新规则生成后清除 Prompt 缓存，下次请求重新从图谱加载
        if new_count > 0:
            try:
                from app.sdk.harness.prompt_assembler import invalidate_prompt_cache

                await invalidate_prompt_cache()  # 清除所有 Agent 的缓存
            except Exception:
                pass

        logger.info(
            f"[SteeringLoop] Analyzed {result['analyzed_checks']} checks, "
            f"found {len(result['high_frequency_failures'])} high-freq failures, "
            f"created {new_count} new policies."
        )
        return result

    except Exception as exc:
        logger.warning(f"[SteeringLoop] Failed: {exc}")
        result["skipped"] = f"Error: {exc}"
        return result
