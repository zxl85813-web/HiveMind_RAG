"""
Core Batch Engine — 基于 LangGraph 的新一代任务编排引擎。

Features:
    - 状态持久化 (Sqlite/Postgres Checkpointer)
    - 动态编排 (Preprocessing -> Branching -> Map-Reduce)
    - 兼容 LangFuse 追踪
    - 支持 Human-in-the-loop (通过 interrupt)

Architecture:
    JobManager (Facade)
        -> LangGraph Workflow
            -> Scheduler Node (Topological Sort)
            -> Worker Node (Async Execution)
"""

import asyncio
from datetime import datetime
from typing import TypedDict, Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemorySaver (Replaced by PickleCheckpointer)
from app.batch.checkpointer import PickleCheckpointer

from loguru import logger
from pydantic import BaseModel

from app.batch.models import BatchJob, TaskUnit, TaskStatus, BatchStatus
from app.batch.task_queue import TaskQueue
from app.batch.models import BatchJob, TaskUnit, TaskStatus, BatchStatus, TaskStep
from app.batch.task_queue import TaskQueue
from app.agents.swarm import SwarmOrchestrator
from app.skills.registry import SkillRegistry
import inspect

# ============================================================
#  Graph State
# ============================================================

class JobState(TypedDict):
    """LangGraph 状态定义"""
    job: BatchJob
    current_tasks: list[TaskUnit]  # 当前正在/将要执行的任务
    error: str | None


# ============================================================
#  Nodes
# ============================================================

class BatchEngineNodes:
    def __init__(self, swarm: SwarmOrchestrator, skills: SkillRegistry):
        self.swarm = swarm
        self.skills = skills

    async def scheduler_node(self, state: JobState) -> dict:
        """
        调度器节点 (Scheduler Node):
        
        核心职责:
        1. 状态同步: 将 Job 的最新状态同步到 TaskQueue。
        2. 依赖解析:通过 TaskQueue 计算 DAG 拓扑，确定哪些任务的前置依赖已满足。
        3. 资源分配: 根据 max_concurrency 限制，决定下一批次执行的任务。
        
        解决的关键问题:
        - 防止死锁: 确保完成的任务能正确解锁下游。
        - 防止无限循环: 确保已完成的任务不会被重复调度 (通过 TaskQueue 状态检查)。
        """
        job = state["job"]
        
        # 0. 检查作业是否整体完成
        total = len(job.tasks)
        terminal_count = sum(1 for t in job.tasks.values() if t.is_terminal)
        
        if terminal_count == total:
            # 所有任务均已终态 (成功/失败/取消)，标记 Job 完成
            job.status = BatchStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            return {"job": job, "current_tasks": []}

        # 1. 重建任务队列 (用于当次调度的依赖计算)
        # 注意: TaskQueue 是临时的，每次调度都会基于 Job 当前状态重建
        queue = TaskQueue(on_failure=job.on_failure)
        queue.add_batch(list(job.tasks.values()))
        
        # 关键: "状态重放" (State Replay)
        # 因为 TaskQueue 是新创建的，我们需要手动告知它哪些任务已经 SUCCESS/FAILED，
        # 这样它才能解锁那些依赖这些任务的下游任务 (将下游标记为 QUEUED)。
        for t in job.tasks.values():
            if t.status == TaskStatus.SUCCESS:
                queue.mark_complete(t.id, success=True)
            elif t.status == TaskStatus.FAILED:
                queue.mark_complete(t.id, success=False)

        # 2. 计算并发配额
        # 正在运行的任务数量
        running_count = sum(1 for t in job.tasks.values() if t.status == TaskStatus.RUNNING)
        # 剩余可用槽位
        available_slots = job.max_concurrency - running_count
        
        tasks_to_run = []
        if available_slots > 0:
            # 获取就绪任务 (依赖已满足且状态为 QUEUED)
            ready_tasks = queue.get_ready_tasks(limit=available_slots)
            for task in ready_tasks:
                # 标记为 RUNNING，防止下一轮重复调度
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                # 更新 Job 对象中的任务状态
                job.tasks[task.id] = task
                tasks_to_run.append(task)
        
        return {"job": job, "current_tasks": tasks_to_run}

    async def worker_node(self, state: JobState) -> dict:
        """
        工作节点 (Worker Node):
        
        核心职责:
        1. 并发执行: 接收 Scheduler 分配的一批任务，使用 asyncio.gather 并行执行。
        2. 状态更新: 执行完成后，将结果 (output/error) 写回 Job 状态。
        
        注意: 目前使用 asyncio.gather 会等待这一批次所有任务完成才返回。
        这是一种"分批同步"模式 (Batch Synchronization)。
        """
        job = state["job"]
        tasks = state.get("current_tasks", [])

        if not tasks:
            return {"job": job}

        logger.info(f"⚙️ Running batch of {len(tasks)} tasks...")

        # 并发执行
        results = await asyncio.gather(
            *[self._execute_single_task(t, job.id) for t in tasks],
            return_exceptions=True
        )

        # 更新状态
        for task, result in zip(tasks, results):
            task.completed_at = datetime.utcnow()
            
            if isinstance(result, Exception):
                task.status = TaskStatus.FAILED
                task.error_message = str(result)
                logger.error(f"Task {task.name} failed: {result}")
            else:
                task.status = TaskStatus.SUCCESS
                task.output_data = result.get("output", {})
                task.step_results = result.get("steps", {})
                logger.info(f"Task {task.name} completed")
            
            # 回写到 Job
            job.tasks[task.id] = task

        return {"job": job, "current_tasks": []}

    async def _execute_single_task(self, task: TaskUnit, job_id: str) -> dict:
        """Execute a single task, dispatching to Skills or defaulting to Swarm."""
        
        # Prepare context (Task Level)
        base_context = {
            "task_id": task.id,
            "job_id": job_id,
            **task.input_data
        }
        
        step_results = {}
        last_output = {}
        
        # If no steps defined, treat the whole task as a single Swarm prompt (Legacy/Simple)
        if not task.steps:
            # Create a virtual step
            task.steps = [TaskStep(name="default_agent_execution", prompt_template=task.input_data.get("prompt", task.name))]

        for step in task.steps:
            logger.info(f"👉 Executing step: {step.name} (Task: {task.name})")
            
            # Strategy 1: Check if step.name matches a registered Skill Tool
            tool_func = self.skills.get_tool(step.name)
            
            if tool_func:
                # Execute Skill Tool
                try:
                    # Map arguments: merge task input + step config + previous step results?
                    # For now: simplistic merge
                    # TODO: Use LLM to map args if complex
                    
                    # Combine inputs
                    combined_args = {**base_context, **step.config}
                    
                    # Inspect function signature to pass only valid args
                    sig = inspect.signature(tool_func)
                    call_args = {}
                    for param_name in sig.parameters:
                        if param_name in combined_args:
                            call_args[param_name] = combined_args[param_name]
                    
                    logger.debug(f"🔧 Invoking tool {step.name} with args: {call_args.keys()}")
                    
                    if inspect.iscoroutinefunction(tool_func):
                        result = await tool_func(**call_args)
                    else:
                        result = tool_func(**call_args)
                        
                    step_results[step.name] = result
                    last_output = result # Update last output
                    
                except Exception as e:
                    logger.error(f"❌ Skill execution failed in step {step.name}: {e}")
                    raise e # Retrying logic handles this
            
            else:
                # Strategy 2: Fallback to Swarm Agent
                # Use step.agent_name or default 'Supervisor'
                prompt = step.prompt_template
                if not prompt: 
                    # If step has no prompt, maybe it's just a config step? Skip or Warn.
                    prompt = f"Execute step {step.name}"
                
                # Context includes previous steps results
                agent_context = {**base_context, "previous_steps": step_results, "step_config": step.config}
                
                response = await self.swarm.invoke(prompt, agent_context)
                
                # Extract Swarm result
                final_msg = response.get("messages", [])[-1].content if response.get("messages") else ""
                
                step_results[step.name] = final_msg
                last_output = {"result": final_msg, "full_state": str(response)}

        return {
            "output": last_output,
            "steps": step_results
        }

# ============================================================
#  Job Manager
# ============================================================

class JobManager:
    """
    基于 LangGraph 的 Job 管理器。
    
    使用:
        manager = JobManager()
        job = manager.create_job(...)
        await manager.start_job(job.id)
    """

    def __init__(self, swarm: SwarmOrchestrator = None, checkpointer=None):
        self.swarm = swarm or SwarmOrchestrator()
        self.skills = SkillRegistry()
        self.nodes = BatchEngineNodes(self.swarm, self.skills)
        # Use persistent checkpointer by default, stored in .checkpoints/batch_engine.pkl
        self.checkpointer = checkpointer or PickleCheckpointer(filepath=".checkpoints/batch_engine.pkl")
        self.graph = self._build_graph()
        self._jobs_index: dict[str, BatchJob] = {}  # Simple in-memory index (TODO: Persist this too?)
        self._skills_loaded = False
    
    def _build_graph(self):
        """Build the LangGraph state machine."""
        workflow = StateGraph(JobState)

        # Add nodes (delegate to BatchEngineNodes)
        workflow.add_node("scheduler", self.nodes.scheduler_node)
        workflow.add_node("worker", self.nodes.worker_node)

        # Add edges
        workflow.set_entry_point("scheduler")
        workflow.add_edge("scheduler", "worker")
        
        # Conditional edge from worker back to scheduler or end
        workflow.add_conditional_edges(
            "worker",
            self._should_continue,
        )

        return workflow.compile(checkpointer=self.checkpointer)

    def _should_continue(self, state: JobState) -> Literal["scheduler", END]:
        """Determine if the job should continue or end."""
        job = state["job"]
        # If job is terminal, stop
        if job.status in (BatchStatus.COMPLETED, BatchStatus.CANCELLED):
            return END
        return "scheduler"

    async def create_job(self, name: str, tasks: list[TaskUnit]) -> BatchJob:
        job = BatchJob(name=name, total_tasks=len(tasks))
        for t in tasks:
            t.batch_job_id = job.id
            job.tasks[t.id] = t
        
        # 保存到索引
        self._jobs_index[job.id] = job
        return job

    async def start_job(self, job_id: str, job_snapshot: BatchJob):
        """启动 Job 执行循环。"""
        # Lazy load skills if not loaded
        if not self._skills_loaded:
            await self.skills.load_all()
            self._skills_loaded = True

        config = {"configurable": {"thread_id": job_id}}
        logger.info(f"🚀 Starting graph for job {job_id}")
        await self.graph.ainvoke(
            {"job": job_snapshot, "current_tasks": []},
            config=config
        )
        logger.info(f"🏁 Graph finished for job {job_id}")

    def get_job(self, job_id: str) -> BatchJob | None:
        """获取最新的 Job 状态 (从 Checkpointer)。"""
        config = {"configurable": {"thread_id": job_id}}
        try:
            snapshot = self.graph.get_state(config)
            if snapshot and snapshot.values and "job" in snapshot.values:
                return snapshot.values["job"]
        except Exception:
            pass
        # Fallback to index (might be stale if graph running)
        return self._jobs_index.get(job_id)

    def list_jobs(self) -> list[BatchJob]:
        """列出所有 Job。"""
        # 理想情况下从 Checkpointer 查询，这里简化为内存索引
        return list(self._jobs_index.values())
        
    async def cancel_job(self, job_id: str):
        """取消 Job (标记状态)。"""
        job = self.get_job(job_id)
        if job:
            job.status = BatchStatus.CANCELLED
            # TODO: 更新 Graph State 以立即停止 (需要 interrupt 或 update_state)
            config = {"configurable": {"thread_id": job_id}}
            current_state = await self.graph.aget_state(config)
            if current_state:
                new_values = current_state.values.copy()
                new_values["job"] = job
                await self.graph.aupdate_state(config, new_values)


