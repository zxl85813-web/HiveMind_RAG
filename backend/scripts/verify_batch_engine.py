"""
Batch Engine Integration Test.
验证基于 LangGraph 的 JobManager 是否能正确处理 DAG 依赖和并发调度。
"""

import asyncio
import sys
import os
from pathlib import Path

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("verify_batch_engine")
t_logger = get_trace_logger("scripts.batch_verify")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.batch.engine import JobManager  # noqa: E402
from app.batch.models import BatchStatus, TaskStatus, TaskUnit  # noqa: E402


async def main():
    t_logger.info("🚀 Starting Batch Engine Test", action="batch_test_start")

    # 1. Initialize Engine (Memory persistence)
    manager = JobManager()

    # 2. Define Tasks with Dependencies
    # Flow: A -> (B, C) -> D
    task_a = TaskUnit(name="Task A (Root)", input_data={"msg": "Start"})
    task_b = TaskUnit(name="Task B (Mid)", depends_on=[task_a.id], input_data={"msg": "Process A"})
    task_c = TaskUnit(name="Task C (Mid)", depends_on=[task_a.id], input_data={"msg": "Process A"})
    task_d = TaskUnit(name="Task D (End)", depends_on=[task_b.id, task_c.id], input_data={"msg": "Aggregate"})

    tasks = [task_a, task_b, task_c, task_d]

    # 3. Create Job
    job = await manager.create_job(name="Test DAG Job", tasks=tasks)
    job.max_concurrency = 2  # Limit concurrency to 2

    t_logger.info(f"📦 Job Created: {job.id} with {len(tasks)} tasks", action="job_create", meta={"job_id": job.id})
    t_logger.info("DAG Structure: A -> (B, C) -> D")

    # 4. Start Job (runs until completion in this script)
    # in production this would be background task
    await manager.start_job(job.id, job)

    # 5. Verify Results
    # Retrieve final state from graph
    config = {"configurable": {"thread_id": job.id}}
    snapshot = await manager.graph.aget_state(config)
    final_job = snapshot.values["job"]

    t_logger.info(f"🏁 Job Status: {final_job.status}", action="job_complete", meta={"status": str(final_job.status)})
    
    # Assertions
    assert final_job.status == BatchStatus.COMPLETED

    # Verify Task Statuses
    for t in final_job.tasks.values():
        t_logger.info(f"   Task [{t.name}] Status: {t.status} (Output: {t.output_data})", action="task_verify")
        assert t.status == TaskStatus.SUCCESS

    # Verify Sequentiality (A finished before B started)
    t_a = final_job.tasks[task_a.id]
    t_b = final_job.tasks[task_b.id]
    assert t_a.completed_at <= t_b.started_at
    
    t_logger.success("✅ Dependency check and Batch Engine Test Passed!", action="audit_success")


if __name__ == "__main__":
    asyncio.run(main())
