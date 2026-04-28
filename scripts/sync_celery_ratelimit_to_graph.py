"""
Celery 限速改动 → Neo4j 图谱同步脚本

将本次 Celery Beat 限速相关的架构变更同步到图谱，建立以下节点和关系：

节点：
  - CeleryConfig      : Celery 配置节点（限速参数）
  - CeleryQueue       : 任务队列节点
  - CeleryTask        : Celery 任务节点
  - BeatSchedule      : Beat 定时调度节点
  - RateLimitPolicy   : 限速策略节点

关系：
  - HAS_RATE_LIMIT    : 任务 → 限速策略
  - ROUTES_TO         : 任务 → 队列
  - SCHEDULED_BY      : 任务 → Beat 调度
  - GOVERNED_BY       : 配置 → 限速策略
  - TRIGGERS          : Beat 调度 → 任务
  - MONITORS          : 日报任务 → 配置

用法：
    cd <project_root>
    python scripts/sync_celery_ratelimit_to_graph.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.sdk.core.graph_store import get_graph_store

# ── 节点定义 ──────────────────────────────────────────────────────────────────

CELERY_CONFIG = {
    "id": "CELERY:config:hivemind_swarm",
    "name": "HiveMind Celery Config",
    "type": "CeleryConfig",
    "path": "backend/app/core/celery_app.py",
    "worker_concurrency": 4,
    "worker_prefetch_multiplier": 1,
    "task_soft_time_limit": 300,
    "task_time_limit": 360,
    "description": "Celery worker 配置，含限速、超时、路由策略",
}

QUEUES = [
    {
        "id": "QUEUE:ingestion_queue",
        "name": "ingestion_queue",
        "type": "CeleryQueue",
        "priority": "high",
        "description": "文档摄入任务队列，受 LLM 配额限速保护",
    },
    {
        "id": "QUEUE:hitl_queue",
        "name": "hitl_queue",
        "type": "CeleryQueue",
        "priority": "medium",
        "description": "人工审核任务队列（低置信度文档）",
    },
    {
        "id": "QUEUE:maintenance_queue",
        "name": "maintenance_queue",
        "type": "CeleryQueue",
        "priority": "low",
        "description": "维护任务队列（内存衰减、可观测性刷新、日报）",
    },
]

TASKS = [
    {
        "id": "TASK:process_document_chunk",
        "name": "process_document_chunk",
        "type": "CeleryTask",
        "path": "backend/app/services/ingestion/tasks.py",
        "queue": "QUEUE:ingestion_queue",
        "rate_limit_id": "RATELIMIT:ingestion",
        "max_retries": 3,
        "acks_late": True,
        "reject_on_worker_lost": True,
        "description": "V3 Swarm 文档处理任务，含指数退避重试",
    },
    {
        "id": "TASK:decay_memory",
        "name": "decay_memory",
        "type": "CeleryTask",
        "path": "backend/app/services/memory/tasks.py",
        "queue": "QUEUE:maintenance_queue",
        "rate_limit_id": "RATELIMIT:maintenance",
        "description": "记忆温度衰减任务，每日凌晨执行",
    },
    {
        "id": "TASK:flush_trace_buffer",
        "name": "flush_trace_buffer",
        "type": "CeleryTask",
        "path": "backend/app/services/observability/tasks.py",
        "queue": "QUEUE:maintenance_queue",
        "rate_limit_id": "RATELIMIT:obs_flush",
        "description": "可观测性 trace buffer 刷新，每 10s 执行",
    },
    {
        "id": "TASK:llm_quota_daily_report",
        "name": "llm_quota_daily_report",
        "type": "CeleryTask",
        "path": "backend/app/services/observability/tasks.py",
        "queue": "QUEUE:maintenance_queue",
        "rate_limit_id": "RATELIMIT:quota_report",
        "description": "LLM 配额日报，统计 24h 调用量/费用/告警",
    },
]

RATE_LIMITS = [
    {
        "id": "RATELIMIT:ingestion",
        "name": "ingestion_rate_limit",
        "type": "RateLimitPolicy",
        "value": "10/m",
        "config_key": "CELERY_INGESTION_RATE_LIMIT",
        "rationale": "防止 LLM API 配额（RPM）被 Celery 瞬间耗尽，每文档约 3-5 次 LLM 调用",
        "hot_reload": True,
        "description": "可通过 update_ingestion_rate_limit() 运行时热更新",
    },
    {
        "id": "RATELIMIT:maintenance",
        "name": "maintenance_rate_limit",
        "type": "RateLimitPolicy",
        "value": "2/m",
        "config_key": "CELERY_MAINTENANCE_RATE_LIMIT",
        "rationale": "低优先级维护任务，避免与 ingestion 竞争 worker 资源",
        "hot_reload": False,
        "description": "内存衰减等低频任务的限速",
    },
    {
        "id": "RATELIMIT:obs_flush",
        "name": "obs_flush_rate_limit",
        "type": "RateLimitPolicy",
        "value": "6/m",
        "config_key": "CELERY_OBS_FLUSH_INTERVAL",
        "rationale": "每 10s 触发一次，限速 6/m 防止 Redis 写入压力",
        "hot_reload": False,
        "description": "可观测性刷新任务限速",
    },
    {
        "id": "RATELIMIT:quota_report",
        "name": "quota_report_rate_limit",
        "type": "RateLimitPolicy",
        "value": "1/h",
        "config_key": "CELERY_LLM_QUOTA_REPORT_HOUR",
        "rationale": "日报任务，严格限速防止重复触发",
        "hot_reload": False,
        "description": "LLM 配额日报限速",
    },
]

BEAT_SCHEDULES = [
    {
        "id": "BEAT:memory-decay-daily",
        "name": "memory-decay-daily",
        "type": "BeatSchedule",
        "schedule": "crontab(hour=3, minute=0)",
        "task_id": "TASK:decay_memory",
        "description": "每天 03:00 UTC 执行内存温度衰减",
    },
    {
        "id": "BEAT:observability-flush",
        "name": "observability-flush-trace-buffer",
        "type": "BeatSchedule",
        "schedule": "every 10s",
        "task_id": "TASK:flush_trace_buffer",
        "description": "每 10 秒刷新 trace buffer 到 PostgreSQL",
    },
    {
        "id": "BEAT:llm-quota-report",
        "name": "llm-quota-daily-report",
        "type": "BeatSchedule",
        "schedule": "crontab(hour=8, minute=0)",
        "task_id": "TASK:llm_quota_daily_report",
        "description": "每天 08:00 UTC 输出 LLM 配额日报",
    },
]

# 配置项 → 限速策略的治理关系
CONFIG_KEYS = [
    {
        "id": "CONFIG:CELERY_INGESTION_RATE_LIMIT",
        "name": "CELERY_INGESTION_RATE_LIMIT",
        "type": "ConfigKey",
        "default": "10/m",
        "path": "backend/app/sdk/core/config.py",
        "governs": "RATELIMIT:ingestion",
    },
    {
        "id": "CONFIG:CELERY_WORKER_CONCURRENCY",
        "name": "CELERY_WORKER_CONCURRENCY",
        "type": "ConfigKey",
        "default": "4",
        "path": "backend/app/sdk/core/config.py",
        "governs": "CELERY:config:hivemind_swarm",
    },
    {
        "id": "CONFIG:CELERY_WORKER_PREFETCH_MULTIPLIER",
        "name": "CELERY_WORKER_PREFETCH_MULTIPLIER",
        "type": "ConfigKey",
        "default": "1",
        "path": "backend/app/sdk/core/config.py",
        "governs": "CELERY:config:hivemind_swarm",
    },
    {
        "id": "CONFIG:CELERY_MAX_RETRIES",
        "name": "CELERY_MAX_RETRIES",
        "type": "ConfigKey",
        "default": "3",
        "path": "backend/app/sdk/core/config.py",
        "governs": "TASK:process_document_chunk",
    },
    {
        "id": "CONFIG:CELERY_RETRY_BACKOFF_BASE",
        "name": "CELERY_RETRY_BACKOFF_BASE",
        "type": "ConfigKey",
        "default": "30",
        "path": "backend/app/sdk/core/config.py",
        "governs": "TASK:process_document_chunk",
    },
]


# ── 同步函数 ──────────────────────────────────────────────────────────────────

async def sync_celery_ratelimit_graph():
    store = get_graph_store()

    if not store.driver:
        print("⚠️  Neo4j not available, skipping graph sync.")
        return

    ts = int(time.time() * 1000)
    print("⚡ Syncing Celery Rate Limit architecture to Neo4j...\n")

    # 1. Celery 主配置节点
    await store.execute_query(
        """
        MERGE (c:ArchNode:CeleryConfig {id: $id})
        SET c.name = $name, c.type = $type, c.path = $path,
            c.worker_concurrency = $worker_concurrency,
            c.worker_prefetch_multiplier = $worker_prefetch_multiplier,
            c.task_soft_time_limit = $task_soft_time_limit,
            c.task_time_limit = $task_time_limit,
            c.description = $description,
            c.updated_at = $ts
        """,
        {**CELERY_CONFIG, "ts": ts},
    )
    print(f"  ✅ CeleryConfig: {CELERY_CONFIG['name']}")

    # 2. 队列节点
    for q in QUEUES:
        await store.execute_query(
            """
            MERGE (q:ArchNode:CeleryQueue {id: $id})
            SET q.name = $name, q.type = $type, q.priority = $priority,
                q.description = $description, q.updated_at = $ts
            """,
            {**q, "ts": ts},
        )
        print(f"  ✅ Queue: {q['name']}")

    # 3. 限速策略节点
    for rl in RATE_LIMITS:
        await store.execute_query(
            """
            MERGE (r:ArchNode:RateLimitPolicy {id: $id})
            SET r.name = $name, r.type = $type, r.value = $value,
                r.config_key = $config_key, r.rationale = $rationale,
                r.hot_reload = $hot_reload, r.description = $description,
                r.updated_at = $ts
            """,
            {**rl, "ts": ts},
        )
        print(f"  ✅ RateLimitPolicy: {rl['name']} ({rl['value']})")

    # 4. 任务节点 + 关系
    for task in TASKS:
        await store.execute_query(
            """
            MERGE (t:ArchNode:CeleryTask {id: $id})
            SET t.name = $name, t.type = $type, t.path = $path,
                t.description = $description, t.updated_at = $ts
            """,
            {**task, "ts": ts},
        )

        # 任务 → 队列
        await store.execute_query(
            """
            MATCH (t:CeleryTask {id: $task_id}), (q:CeleryQueue {id: $queue_id})
            MERGE (t)-[:ROUTES_TO]->(q)
            """,
            {"task_id": task["id"], "queue_id": task["queue"]},
        )

        # 任务 → 限速策略
        await store.execute_query(
            """
            MATCH (t:CeleryTask {id: $task_id}), (r:RateLimitPolicy {id: $rl_id})
            MERGE (t)-[:HAS_RATE_LIMIT]->(r)
            """,
            {"task_id": task["id"], "rl_id": task["rate_limit_id"]},
        )

        # 关联到已有的 File 节点（如果存在）
        await store.execute_query(
            """
            MATCH (t:CeleryTask {id: $task_id})
            OPTIONAL MATCH (f:ArchNode:File {id: $path})
            FOREACH (_ IN CASE WHEN f IS NOT NULL THEN [1] ELSE [] END |
                MERGE (f)-[:DEFINES_TASK]->(t)
            )
            """,
            {"task_id": task["id"], "path": task["path"]},
        )
        print(f"  ✅ CeleryTask: {task['name']} → {task['queue'].split(':')[1]}")

    # 5. Beat 调度节点 + 关系
    for beat in BEAT_SCHEDULES:
        await store.execute_query(
            """
            MERGE (b:ArchNode:BeatSchedule {id: $id})
            SET b.name = $name, b.type = $type, b.schedule = $schedule,
                b.description = $description, b.updated_at = $ts
            """,
            {**beat, "ts": ts},
        )

        # Beat → 任务
        await store.execute_query(
            """
            MATCH (b:BeatSchedule {id: $beat_id}), (t:CeleryTask {id: $task_id})
            MERGE (b)-[:TRIGGERS]->(t)
            """,
            {"beat_id": beat["id"], "task_id": beat["task_id"]},
        )
        print(f"  ✅ BeatSchedule: {beat['name']} ({beat['schedule']})")

    # 6. 配置键节点 + 治理关系
    for ck in CONFIG_KEYS:
        await store.execute_query(
            """
            MERGE (k:ArchNode:ConfigKey {id: $id})
            SET k.name = $name, k.type = $type, k.default = $default,
                k.path = $path, k.updated_at = $ts
            """,
            {**ck, "ts": ts},
        )

        # ConfigKey → 被治理的节点
        await store.execute_query(
            """
            MATCH (k:ConfigKey {id: $key_id})
            OPTIONAL MATCH (target {id: $governs_id})
            FOREACH (_ IN CASE WHEN target IS NOT NULL THEN [1] ELSE [] END |
                MERGE (k)-[:GOVERNS]->(target)
            )
            """,
            {"key_id": ck["id"], "governs_id": ck["governs"]},
        )
        print(f"  ✅ ConfigKey: {ck['name']} = {ck['default']}")

    # 7. 日报任务监控 Celery 配置（特殊关系）
    await store.execute_query(
        """
        MATCH (t:CeleryTask {id: 'TASK:llm_quota_daily_report'}),
              (c:CeleryConfig {id: 'CELERY:config:hivemind_swarm'})
        MERGE (t)-[:MONITORS]->(c)
        """,
        {},
    )

    # 8. Celery 配置 → 限速策略（整体治理关系）
    for rl in RATE_LIMITS:
        await store.execute_query(
            """
            MATCH (c:CeleryConfig {id: 'CELERY:config:hivemind_swarm'}),
                  (r:RateLimitPolicy {id: $rl_id})
            MERGE (c)-[:GOVERNED_BY]->(r)
            """,
            {"rl_id": rl["id"]},
        )

    print(f"""
⚡ Celery Rate Limit Graph Sync Complete!
   CeleryConfig  : 1
   Queues        : {len(QUEUES)}
   Tasks         : {len(TASKS)}
   RateLimits    : {len(RATE_LIMITS)}
   BeatSchedules : {len(BEAT_SCHEDULES)}
   ConfigKeys    : {len(CONFIG_KEYS)}
""")


if __name__ == "__main__":
    asyncio.run(sync_celery_ratelimit_graph())
