"""
Worker Pool — 并发控制与 Swarm 调用。

核心机制:
    1. Semaphore 控制同时运行的 Swarm 调用数 (防 LLM rate limit)
    2. 每个 Worker 是一个独立的 asyncio.Task
    3. Worker 从 TaskQueue 取任务、调 Swarm、写回结果
    4. 支持超时、重试、取消
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from loguru import logger

from app.batch.models import TaskStatus, TaskUnit


class WorkerPool:
    """
    管理一组并发 Worker，每个 Worker 执行一个 TaskUnit。

    关键设计:
        - Semaphore 做背压: 即使队列里有 1000 个任务，
          同一时刻最多只有 max_concurrency 个在调用 LLM API
        - 每个 Worker 是短生命周期的: 取一个任务 → 执行 → 结束
        - Pool 本身是长生命周期的: 持续从队列取任务并 spawn Worker
    """

    def __init__(
        self,
        max_concurrency: int = 5,
        task_timeout: int = 120,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_concurrency = max_concurrency
        self._task_timeout = task_timeout
        self._active_workers: dict[str, asyncio.Task] = {}  # task_id → asyncio.Task
        self._execute_fn: Callable[[TaskUnit], Awaitable[dict[str, Any]]] | None = None
        self._on_complete: Callable[[TaskUnit], Awaitable[None]] | None = None
        logger.info(f"⚙️ WorkerPool initialized (concurrency={max_concurrency}, timeout={task_timeout}s)")

    def set_executor(self, fn: Callable[[TaskUnit], Awaitable[dict[str, Any]]]) -> None:
        """
        注入实际的任务执行函数。

        这个函数接收一个 TaskUnit，返回结果 dict。
        通常是: SwarmOrchestrator.invoke() 的封装。
        """
        self._execute_fn = fn

    def set_completion_callback(self, fn: Callable[[TaskUnit], Awaitable[None]]) -> None:
        """任务完成 (成功或失败) 后的回调。用于通知 BatchController 更新状态。"""
        self._on_complete = fn

    async def submit(self, task: TaskUnit) -> None:
        """
        提交一个任务到 Worker Pool。

        不会阻塞 — 立即返回。
        实际执行会等 Semaphore 有空位。
        """
        worker = asyncio.create_task(self._run_worker(task))
        self._active_workers[task.id] = worker

    async def _run_worker(self, task: TaskUnit) -> None:
        """
        单个 Worker 的执行逻辑:
            1. 获取信号量 (背压控制)
            2. 更新状态为 RUNNING
            3. 调用执行函数 (带超时)
            4. 处理成功/失败
            5. 释放信号量
        """
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            worker_id = f"worker-{id(asyncio.current_task())}"
            task.worker_id = worker_id

            logger.info(f"🔧 [{worker_id}] 开始执行: {task.name} (id={task.id[:8]})")

            try:
                if not self._execute_fn:
                    raise RuntimeError("No executor function set")

                # 带超时执行
                result = await asyncio.wait_for(
                    self._execute_fn(task),
                    timeout=self._task_timeout,
                )

                # 成功
                task.status = TaskStatus.SUCCESS
                task.output_data = result
                task.completed_at = datetime.utcnow()
                logger.success(f"✅ [{worker_id}] 完成: {task.name} (耗时 {task.duration_seconds:.1f}s)")

            except TimeoutError:
                task.status = TaskStatus.FAILED
                task.error_message = f"Timeout after {self._task_timeout}s"
                task.completed_at = datetime.utcnow()
                logger.error(f"⏰ [{worker_id}] 超时: {task.name}")

            except Exception as e:
                # 判断是否需要重试
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.RETRY_WAIT
                    task.error_message = f"Attempt {task.retry_count}/{task.max_retries}: {e!s}"
                    logger.warning(f"🔄 [{worker_id}] 重试 ({task.retry_count}/{task.max_retries}): {task.name} — {e}")
                else:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    task.completed_at = datetime.utcnow()
                    logger.error(f"❌ [{worker_id}] 失败: {task.name} — {e}")

            finally:
                # 从 active 中移除
                self._active_workers.pop(task.id, None)

                # 通知完成
                if self._on_complete:
                    await self._on_complete(task)

    async def cancel_task(self, task_id: str) -> bool:
        """取消一个正在执行的任务。"""
        worker = self._active_workers.get(task_id)
        if worker and not worker.done():
            worker.cancel()
            logger.info(f"🚫 Task cancelled: {task_id[:8]}")
            return True
        return False

    async def cancel_all(self) -> int:
        """取消所有正在执行的任务。"""
        count = 0
        for task_id in list(self._active_workers.keys()):
            if await self.cancel_task(task_id):
                count += 1
        return count

    @property
    def active_count(self) -> int:
        return len(self._active_workers)

    @property
    def available_slots(self) -> int:
        """当前还能接受多少个并发任务。"""
        # Semaphore 的内部计数器没有公开 API，用 active_count 估算
        return max(0, self._max_concurrency - self.active_count)
