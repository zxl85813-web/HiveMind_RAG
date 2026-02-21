"""
Task Queue — DAG 依赖管理 + 优先级调度。

职责:
    1. 管理 TaskUnit 的状态转移
    2. 解析依赖关系 (DAG)，确定哪些任务可以执行
    3. 按优先级输出就绪任务
    4. 检测循环依赖
"""

from collections import defaultdict
from typing import Any

from loguru import logger

from app.batch.models import TaskUnit, TaskStatus, TaskPriority


class TaskQueue:
    """
    基于 DAG 的任务队列。

    核心概念:
        - 就绪 (ready): 所有依赖都已 SUCCESS，可以提交给 WorkerPool
        - 阻塞 (blocked): 还有依赖未完成
        - 失败传播: 如果依赖失败，选择跳过或级联失败

    示例:
        queue = TaskQueue()
        queue.add(task_a)  # 无依赖
        queue.add(task_b, depends_on=[task_a.id])  # B 依赖 A
        queue.add(task_c)  # 无依赖

        ready = queue.get_ready_tasks()
        # → [task_a, task_c]  (task_b 被阻塞)

        queue.mark_complete(task_a.id)
        ready = queue.get_ready_tasks()
        # → [task_b]  (依赖已满足)
    """

    def __init__(self, on_failure: str = "continue") -> None:
        """
        Args:
            on_failure: 依赖失败时的策略
                - "continue": 跳过依赖失败的任务 (标记为 CANCELLED)
                - "stop": 停止整个 BatchJob
                - "ignore": 忽略失败的依赖，继续执行
        """
        self._tasks: dict[str, TaskUnit] = {}
        # 反向索引: task_id → set of task_ids that depend on it
        self._dependents: dict[str, set[str]] = defaultdict(set)
        self._on_failure = on_failure
        logger.info(f"📋 TaskQueue initialized (on_failure={on_failure})")

    def add(self, task: TaskUnit) -> None:
        """添加任务到队列。"""
        self._tasks[task.id] = task

        # 构建反向依赖索引
        for dep_id in task.depends_on:
            self._dependents[dep_id].add(task.id)

        # 如果没有依赖且状态为 PENDING，标记为 QUEUED
        # 修复说明: 之前这里无条件重置为 QUEUED，导致 Scheduler 在重建队列时，
        # 会把已经 SUCCESS 的根节点任务重置为 QUEUED，从而引发无限循环执行。
        # 现在只对初始状态 (PENDING) 的任务进行自动入队。
        if not task.depends_on and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.QUEUED

        logger.debug(f"📥 Task added: {task.name} (deps={len(task.depends_on)})")

    def add_batch(self, tasks: list[TaskUnit]) -> None:
        """批量添加任务。"""
        for task in tasks:
            self.add(task)

        # 检测循环依赖
        if self._has_cycle():
            raise ValueError("Circular dependency detected in task graph!")

        logger.info(f"📋 Batch added: {len(tasks)} tasks, {self._count_edges()} dependencies")

    def get_ready_tasks(self, limit: int = 10) -> list[TaskUnit]:
        """
        获取所有可执行的任务 (依赖已满足 + 状态为 QUEUED)。
        按优先级降序排列。
        """
        ready = []
        for task in self._tasks.values():
            if task.status == TaskStatus.QUEUED:
                ready.append(task)
            elif task.status == TaskStatus.RETRY_WAIT:
                # 重试的任务也可以重新执行
                ready.append(task)

        # 按优先级排序 (高优先级先执行)
        ready.sort(key=lambda t: t.priority.value, reverse=True)
        return ready[:limit]

    def mark_complete(self, task_id: str, success: bool = True) -> list[str]:
        """
        标记任务完成，并解锁下游任务。

        Returns:
            新变为 QUEUED 状态的下游任务 ID 列表
        """
        task = self._tasks.get(task_id)
        if not task:
            return []

        newly_ready: list[str] = []

        if success:
            # 检查所有依赖此任务的下游任务
            for dependent_id in self._dependents.get(task_id, set()):
                dependent = self._tasks.get(dependent_id)
                if not dependent or dependent.is_terminal:
                    continue

                # 检查该下游任务的所有依赖是否都已完成
                all_deps_met = all(
                    self._tasks.get(dep_id) and self._tasks[dep_id].status == TaskStatus.SUCCESS
                    for dep_id in dependent.depends_on
                )

                if all_deps_met:
                    dependent.status = TaskStatus.QUEUED
                    newly_ready.append(dependent_id)
                    logger.debug(f"🔓 Unblocked: {dependent.name}")
        else:
            # 依赖失败 — 根据策略处理下游
            self._handle_dependency_failure(task_id)

        return newly_ready

    def _handle_dependency_failure(self, failed_task_id: str) -> None:
        """处理依赖失败的级联效应。"""
        for dependent_id in self._dependents.get(failed_task_id, set()):
            dependent = self._tasks.get(dependent_id)
            if not dependent or dependent.is_terminal:
                continue

            if self._on_failure == "continue":
                dependent.status = TaskStatus.CANCELLED
                dependent.error_message = f"Dependency {failed_task_id[:8]} failed"
                logger.warning(f"⏭️ Skipped (dep failed): {dependent.name}")
                # 级联取消
                self._handle_dependency_failure(dependent_id)

            elif self._on_failure == "ignore":
                # 移除失败的依赖，检查剩余依赖
                remaining_deps = [
                    d for d in dependent.depends_on
                    if self._tasks.get(d) and self._tasks[d].status != TaskStatus.FAILED
                ]
                all_met = all(
                    self._tasks[d].status == TaskStatus.SUCCESS
                    for d in remaining_deps
                )
                if all_met:
                    dependent.status = TaskStatus.QUEUED

    def get_task(self, task_id: str) -> TaskUnit | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[TaskUnit]:
        return list(self._tasks.values())

    # --- 内部工具 ---

    def _has_cycle(self) -> bool:
        """拓扑排序检测循环依赖。"""
        in_degree: dict[str, int] = {tid: 0 for tid in self._tasks}
        for task in self._tasks.values():
            for dep in task.depends_on:
                if dep in in_degree:
                    in_degree[task.id] = in_degree.get(task.id, 0) + 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        visited = 0

        while queue:
            node = queue.pop(0)
            visited += 1
            for dependent_id in self._dependents.get(node, set()):
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        return visited != len(self._tasks)

    def _count_edges(self) -> int:
        return sum(len(t.depends_on) for t in self._tasks.values())
