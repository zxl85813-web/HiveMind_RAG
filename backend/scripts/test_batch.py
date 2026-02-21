"""
批处理引擎测试脚本。

模拟场景: 10 篇文档的批量分析
    - 3 篇独立任务 (并行)
    - 4 篇有依赖链 (A→B→C→D)
    - 3 篇依赖同一个前置任务

测试重点:
    1. 并发控制 (max_concurrency=3)
    2. DAG 依赖: B 等 A 完成才开始
    3. 进度追踪: 实时打印进度
    4. 故障恢复: 其中一个任务 Mock 失败 + 重试
"""

import asyncio
import os
import sys
from pathlib import Path

# Setup path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from loguru import logger
from app.batch.models import TaskUnit, TaskStep, TaskPriority
from app.batch.controller import BatchController


async def main():
    logger.info("🚀 批处理引擎测试开始")

    # ============================================================
    #  1. 创建 Controller (不注入 Swarm，用 Mock 执行)
    # ============================================================
    controller = BatchController(swarm_invoke_fn=None)  # None = Mock 模式

    # ============================================================
    #  2. 构造任务
    # ============================================================
    tasks: list[TaskUnit] = []

    # --- 3 篇独立文档 (无依赖, 可并行) ---
    for i in range(3):
        tasks.append(TaskUnit(
            name=f"独立分析-文档{i+1}",
            input_data={"prompt": f"分析第 {i+1} 篇独立文档"},
            steps=[TaskStep(name="summarize", agent_name="rag_agent")],
            priority=TaskPriority.NORMAL,
        ))

    # --- 4 篇串行依赖链 (A → B → C → D) ---
    chain_tasks: list[TaskUnit] = []
    for i in range(4):
        t = TaskUnit(
            name=f"链式分析-阶段{i+1}",
            input_data={"prompt": f"链式处理阶段 {i+1}/4"},
            steps=[TaskStep(name=f"step_{i}", agent_name="code_agent")],
            priority=TaskPriority.HIGH,
        )
        if chain_tasks:
            t.depends_on = [chain_tasks[-1].id]
        chain_tasks.append(t)
    tasks.extend(chain_tasks)

    # --- 3 篇共享依赖 (都依赖链式任务的第一个) ---
    for i in range(3):
        tasks.append(TaskUnit(
            name=f"扇出分析-文档{i+1}",
            input_data={"prompt": f"基于阶段1的结果，分析扇出文档 {i+1}"},
            depends_on=[chain_tasks[0].id],  # 都依赖第一个链式任务
            priority=TaskPriority.LOW,
        ))

    logger.info(f"📋 共创建 {len(tasks)} 个任务")

    # ============================================================
    #  3. 创建 Job 并启动
    # ============================================================
    job = controller.create_job(
        name="文档批量分析测试",
        tasks=tasks,
        max_concurrency=3,
        timeout_per_task=30,
        on_failure="continue",
    )

    await controller.start_job(job.id)

    # ============================================================
    #  4. 轮询进度
    # ============================================================
    while True:
        await asyncio.sleep(1)
        progress = controller.get_progress(job.id)

        if not progress:
            break

        status = progress["status"]
        logger.info(
            f"📊 进度: {progress['progress']} | "
            f"完成率={progress['completion_rate']} | "
            f"活跃Worker={progress['active_workers']} | "
            f"耗时={progress['elapsed_seconds']:.1f}s"
        )

        if status in ("completed", "partial", "failed", "cancelled"):
            break

    # ============================================================
    #  5. 输出最终结果
    # ============================================================
    final_job = controller.get_job(job.id)
    if final_job:
        logger.success(f"\n{'='*60}")
        logger.success(f"🏁 Job: {final_job.name}")
        logger.success(f"   状态: {final_job.status.value}")
        logger.success(f"   成功率: {final_job.success_rate:.0%}")
        logger.success(f"   任务详情:")
        for task in final_job.tasks.values():
            logger.success(
                f"     [{task.status.value:>10}] {task.name}"
                f" {'(耗时 ' + f'{task.duration_seconds:.1f}s)' if task.duration_seconds else ''}"
            )


if __name__ == "__main__":
    asyncio.run(main())
