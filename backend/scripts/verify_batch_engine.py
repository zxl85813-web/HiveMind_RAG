"""
Batch Engine Integration Test.
验证基于 LangGraph 的 JobManager 是否能正确处理 DAG 依赖和并发调度。
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))
load_dotenv(backend_dir / ".env")

from loguru import logger  # noqa: E402

from app.batch.engine import JobManager  # noqa: E402
from app.batch.models import BatchStatus, TaskStatus, TaskUnit  # noqa: E402


async def main():
    logger.info("🚀 Starting Batch Engine Test")

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

    logger.info(f"📦 Job Created: {job.id} with {len(tasks)} tasks")
    logger.info("DAG Structure: A -> (B, C) -> D")

    # 4. Start Job (runs until completion in this script)
    # in production this would be background task
    await manager.start_job(job.id, job)

    # 5. Verify Results
    # Retrieve final state from graph
    config = {"configurable": {"thread_id": job.id}}
    snapshot = await manager.graph.aget_state(config)
    final_job = snapshot.values["job"]

    logger.info(f"🏁 Job Status: {final_job.status}")
    logger.info(f"   Duration: {final_job.completed_at - final_job.created_at}")

    # Assertions
    assert final_job.status == BatchStatus.COMPLETED

    # Verify Task Statuses
    for t in final_job.tasks.values():
        logger.info(f"   Task [{t.name}] Status: {t.status} (Output: {t.output_data})")
        assert t.status == TaskStatus.SUCCESS

    # Verify Sequentiality (A finished before B started)
    t_a = final_job.tasks[task_a.id]
    t_b = final_job.tasks[task_b.id]
    assert t_a.completed_at <= t_b.started_at
    logger.success("✅ Dependency check: A completed before B started")

    logger.success("✅ Batch Engine Test Passed!")


if __name__ == "__main__":
    asyncio.run(main())
