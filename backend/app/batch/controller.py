"""
Batch Controller — 批处理引擎的顶层编排器。

职责:
    1. 接收批处理请求，拆解为 TaskUnit
    2. 组装 TaskQueue + WorkerPool
    3. 驱动执行循环: 取就绪任务 → 提交 Worker → 等完成 → 解锁下游
    4. 汇报进度
    5. 管理 Job 生命周期

使用方式:
    controller = BatchController(swarm=swarm_orchestrator)

    # 创建 Job
    job = controller.create_job("论文批量分析", tasks=[...])

    # 启动 (非阻塞)
    await controller.start_job(job.id)

    # 查询进度
    progress = controller.get_progress(job.id)
    # → {"total": 100, "success": 42, "running": 5, "pending": 53}

    # 取消
    await controller.cancel_job(job.id)
"""

import asyncio
from datetime import datetime
from typing import Any

from loguru import logger

from app.batch.models import (
    BatchJob,
    BatchStatus,
    TaskStatus,
    TaskUnit,
)
from app.batch.task_queue import TaskQueue
from app.batch.worker_pool import WorkerPool


class BatchController:
    """
    [DEPRECATED] 批处理引擎的顶层控制器。

    Replaced by: app.batch.engine.JobManager
    Please use JobManager for all new batch processing tasks.
    """

    def __init__(self, swarm_invoke_fn: Any = None) -> None:
        import warnings

        warnings.warn("BatchController is deprecated, use JobManager instead", DeprecationWarning, stacklevel=2)

        """
        Args:
            swarm_invoke_fn: Swarm 调用函数。
                签名: async def fn(task: TaskUnit) -> dict[str, Any]
                通常是 SwarmOrchestrator.invoke() 的封装。
        """
        self._jobs: dict[str, BatchJob] = {}
        self._queues: dict[str, TaskQueue] = {}
        self._pools: dict[str, WorkerPool] = {}
        self._job_loops: dict[str, asyncio.Task] = {}  # 每个 Job 的驱动循环
        self._swarm_invoke_fn = swarm_invoke_fn
        logger.info("🎛️ BatchController initialized")

    # ============================================================
    #  Job 生命周期
    # ============================================================

    def create_job(
        self,
        name: str,
        tasks: list[TaskUnit],
        max_concurrency: int = 5,
        timeout_per_task: int = 120,
        on_failure: str = "continue",
    ) -> BatchJob:
        """
        创建一个批处理作业。

        Args:
            name: 作业名称
            tasks: 任务列表 (可以包含依赖关系)
            max_concurrency: 最大并发 Swarm 调用数
            timeout_per_task: 每个任务的超时秒数
            on_failure: 依赖失败策略 ("continue" | "stop" | "ignore")
        """
        job = BatchJob(
            name=name,
            total_tasks=len(tasks),
            max_concurrency=max_concurrency,
            timeout_per_task=timeout_per_task,
            on_failure=on_failure,
        )

        # 关联任务
        for task in tasks:
            task.batch_job_id = job.id
            job.tasks[task.id] = task

        self._jobs[job.id] = job
        logger.info(f"📦 Job created: {name} ({len(tasks)} tasks, concurrency={max_concurrency})")
        return job

    async def start_job(self, job_id: str) -> None:
        """启动一个批处理作业 (非阻塞)。"""
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job.status == BatchStatus.RUNNING:
            raise ValueError(f"Job already running: {job_id}")

        # 初始化队列和池
        queue = TaskQueue(on_failure=job.on_failure)
        pool = WorkerPool(
            max_concurrency=job.max_concurrency,
            task_timeout=job.timeout_per_task,
        )

        # 注入执行函数
        pool.set_executor(self._create_task_executor(job_id))
        pool.set_completion_callback(self._create_completion_handler(job_id))

        # 加载所有任务到队列
        queue.add_batch(list(job.tasks.values()))

        self._queues[job_id] = queue
        self._pools[job_id] = pool

        # 更新状态
        job.status = BatchStatus.RUNNING
        job.started_at = datetime.utcnow()

        # 启动驱动循环
        loop_task = asyncio.create_task(self._drive_loop(job_id))
        self._job_loops[job_id] = loop_task

        logger.info(f"🚀 Job started: {job.name}")

    async def cancel_job(self, job_id: str) -> None:
        """取消一个正在运行的作业。"""
        job = self._jobs.get(job_id)
        if not job:
            return

        # 取消驱动循环
        loop_task = self._job_loops.get(job_id)
        if loop_task and not loop_task.done():
            loop_task.cancel()

        # 取消所有 Worker
        pool = self._pools.get(job_id)
        if pool:
            cancelled = await pool.cancel_all()
            logger.info(f"Cancelled {cancelled} active workers")

        # 标记未完成的任务
        for task in job.tasks.values():
            if not task.is_terminal:
                task.status = TaskStatus.CANCELLED

        job.status = BatchStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        logger.info(f"🚫 Job cancelled: {job.name}")

    # ============================================================
    #  驱动循环 — 核心调度引擎
    # ============================================================

    async def _drive_loop(self, job_id: str) -> None:
        """
        持续驱动一个 Job 的执行:
            1. 从队列取就绪任务
            2. 提交给 WorkerPool
            3. 等待一小段时间 (避免忙等)
            4. 重复，直到所有任务完成
        """
        job = self._jobs[job_id]
        queue = self._queues[job_id]
        pool = self._pools[job_id]

        logger.info(f"🔄 Drive loop started for: {job.name}")

        try:
            while True:
                # 检查是否所有任务已到终态
                all_terminal = all(t.is_terminal for t in job.tasks.values())
                if all_terminal:
                    break

                # 获取就绪任务 (限制为 Worker 空位数)
                available = pool.available_slots
                if available > 0:
                    ready_tasks = queue.get_ready_tasks(limit=available)
                    for task in ready_tasks:
                        task.status = TaskStatus.RUNNING  # 防止重复提交
                        await pool.submit(task)

                # 短暂等待，避免忙等
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info(f"Drive loop cancelled for: {job.name}")
            return

        # 完成，计算最终状态
        self._finalize_job(job)

    def _finalize_job(self, job: BatchJob) -> None:
        """计算最终 Job 状态。"""
        job.completed_at = datetime.utcnow()

        success_count = sum(1 for t in job.tasks.values() if t.status == TaskStatus.SUCCESS)
        total = len(job.tasks)

        if success_count == total:
            job.status = BatchStatus.COMPLETED
        elif success_count == 0:
            job.status = BatchStatus.FAILED
        else:
            job.status = BatchStatus.PARTIAL

        duration = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
        logger.info(
            f"🏁 Job finished: {job.name} | "
            f"Status={job.status.value} | "
            f"Success={success_count}/{total} ({job.success_rate:.0%}) | "
            f"Duration={duration:.1f}s"
        )

    # ============================================================
    #  执行函数工厂
    # ============================================================

    def _create_task_executor(self, job_id: str):
        """
        创建 TaskUnit 的执行函数。

        这个函数封装了:
            1. 从 TaskUnit 提取 input_data
            2. 构造 Swarm 调用的 prompt
            3. 调用 Swarm
            4. 解析结果
        """

        async def execute(task: TaskUnit) -> dict[str, Any]:
            if self._swarm_invoke_fn:
                # 真实执行: 调用 Swarm
                prompt = task.input_data.get("prompt", task.name)
                context = {
                    "batch_job_id": job_id,
                    "task_id": task.id,
                    "step_results": task.step_results,
                    **task.input_data,
                }
                result = await self._swarm_invoke_fn(prompt, context)
                return {"swarm_result": result}
            else:
                # Mock 执行 (用于测试)
                await asyncio.sleep(0.5)
                return {"mock": True, "task_name": task.name}

        return execute

    def _create_completion_handler(self, job_id: str):
        """任务完成后的回调: 通知 TaskQueue 解锁下游。"""

        async def on_complete(task: TaskUnit) -> None:
            queue = self._queues.get(job_id)
            if not queue:
                return

            success = task.status == TaskStatus.SUCCESS
            newly_ready = queue.mark_complete(task.id, success=success)

            if newly_ready:
                logger.debug(f"🔓 {len(newly_ready)} downstream tasks unblocked")

            # 如果是 RETRY_WAIT，重新入队
            if task.status == TaskStatus.RETRY_WAIT:
                task.status = TaskStatus.QUEUED  # 回到就绪状态

        return on_complete

    # ============================================================
    #  查询接口
    # ============================================================

    def get_job(self, job_id: str) -> BatchJob | None:
        return self._jobs.get(job_id)

    def get_progress(self, job_id: str) -> dict[str, Any]:
        """获取 Job 的实时进度。"""
        job = self._jobs.get(job_id)
        if not job:
            return {}

        pool = self._pools.get(job_id)

        return {
            "job_id": job_id,
            "job_name": job.name,
            "status": job.status.value,
            "total": len(job.tasks),
            "progress": job.progress,
            "completion_rate": f"{job.completion_rate:.0%}",
            "success_rate": f"{job.success_rate:.0%}",
            "active_workers": pool.active_count if pool else 0,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "elapsed_seconds": ((datetime.utcnow() - job.started_at).total_seconds() if job.started_at else 0),
        }

    def list_jobs(self) -> list[dict[str, Any]]:
        """列出所有 Job 的摘要。"""
        return [
            {
                "id": job.id,
                "name": job.name,
                "status": job.status.value,
                "total": len(job.tasks),
                "completion_rate": f"{job.completion_rate:.0%}",
            }
            for job in self._jobs.values()
        ]
