"""
Batch Processing — 数据模型。

TaskUnit 是最小调度单元，BatchJob 是一组 TaskUnit 的集合。
TaskUnit 之间可以有依赖关系 (DAG)。
"""

import uuid
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================
#  枚举
# ============================================================


class TaskStatus(StrEnum):
    """任务状态机: PENDING → QUEUED → RUNNING → SUCCESS/FAILED/CANCELLED"""

    PENDING = "pending"  # 等待依赖完成
    QUEUED = "queued"  # 已入队，等待 Worker
    RUNNING = "running"  # Worker 正在执行
    SUCCESS = "success"  # 执行成功
    FAILED = "failed"  # 执行失败 (已耗尽重试)
    CANCELLED = "cancelled"  # 被取消
    RETRY_WAIT = "retry_wait"  # 等待重试


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class BatchStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"  # 所有任务成功
    PARTIAL = "partial"  # 部分成功
    FAILED = "failed"  # 全部失败
    CANCELLED = "cancelled"


# ============================================================
#  TaskUnit — 最小调度单元
# ============================================================


class TaskStep(BaseModel):
    """任务内的单个执行步骤。"""

    name: str  # 如 "parse", "summarize", "classify"
    agent_name: str | None = None  # 指定 Agent，None 则由 Supervisor 路由
    prompt_template: str = ""  # 步骤的 Prompt 模板
    config: dict[str, Any] = {}  # 步骤配置


class TaskUnit(BaseModel):
    """一个最小可调度的任务单元。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_job_id: str = ""

    # --- 任务定义 ---
    name: str  # 人类可读名称, 如 "分析论文: attention.pdf"
    input_data: dict[str, Any] = {}  # 输入数据 (文件路径、文本、URL 等)
    steps: list[TaskStep] = []  # 执行步骤链 (按顺序执行)

    # --- DAG 依赖 ---
    depends_on: list[str] = []  # 依赖的其他 TaskUnit ID

    # --- 调度信息 ---
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3

    # --- 结果 ---
    output_data: dict[str, Any] = {}  # 执行结果
    error_message: str = ""
    step_results: dict[str, Any] = {}  # 每个 step 的中间结果

    # --- 时间线 ---
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # --- 追踪 ---
    worker_id: str = ""  # 哪个 Worker 在处理
    swarm_trace: list[dict] = []  # Swarm 执行的完整追踪日志

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_terminal(self) -> bool:
        """是否已到终态 (不会再变)。"""
        return self.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED)


# ============================================================
#  BatchJob — 批处理作业
# ============================================================


class BatchJob(BaseModel):
    """一次批处理作业，包含多个 TaskUnit。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # 如 "论文批量分析 2026-02-17"
    description: str = ""

    # --- 任务集合 ---
    tasks: dict[str, TaskUnit] = {}  # task_id → TaskUnit
    total_tasks: int = 0

    # --- 状态 ---
    status: BatchStatus = BatchStatus.CREATED

    # --- 配置 ---
    max_concurrency: int = 5  # 最大并发 Swarm 调用数
    timeout_per_task: int = 120  # 每个任务的超时秒数
    on_failure: str = "continue"  # "continue" | "stop" | "retry"

    # --- 时间线 ---
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # --- 统计 ---
    @property
    def progress(self) -> dict[str, int]:
        counts = {}
        for task in self.tasks.values():
            counts[task.status.value] = counts.get(task.status.value, 0) + 1
        return counts

    @property
    def completion_rate(self) -> float:
        if not self.tasks:
            return 0.0
        terminal = sum(1 for t in self.tasks.values() if t.is_terminal)
        return terminal / len(self.tasks)

    @property
    def success_rate(self) -> float:
        if not self.tasks:
            return 0.0
        success = sum(1 for t in self.tasks.values() if t.status == TaskStatus.SUCCESS)
        return success / len(self.tasks)
