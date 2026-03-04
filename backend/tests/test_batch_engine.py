import asyncio
import pytest
from app.batch.models import BatchJob, TaskUnit, TaskStep, TaskStatus, BatchStatus
from app.batch.engine import JobManager

@pytest.mark.asyncio
async def test_batch_engine_simple_dag():
    manager = JobManager()
    
    # Create 3 tasks: A, B, C; C depends on A and B
    task_a = TaskUnit(name="Task A", steps=[TaskStep(name="echo", config={"message": "Result A"})])
    task_b = TaskUnit(name="Task B", steps=[TaskStep(name="echo", config={"message": "Result B"})])
    task_c = TaskUnit(name="Task C", depends_on=[task_a.id, task_b.id], steps=[TaskStep(name="echo", config={"message": "Result C"})])
    
    job = await manager.create_job("Test Job", [task_a, task_b, task_c])
    
    # To mock the tool execution without actual tools/swarm, we'll patch the engine's _execute_single_task
    # Let's write a small wrapper to intercept
    original_exec = manager.nodes._execute_single_task
    
    async def mock_exec(task, job_id):
        # simulate some delay
        await asyncio.sleep(0.1)
        return {"output": {"result": f"Mock output for {task.name}"}, "steps": {}}
        
    manager.nodes._execute_single_task = mock_exec
    
    try:
        await manager.start_job(job.id, job)
        
        # Verify job completed
        final_job = manager.get_job(job.id)
        assert final_job.status == BatchStatus.COMPLETED
        
        # Verify all tasks succeeded
        for task in final_job.tasks.values():
            assert task.status == TaskStatus.SUCCESS
            assert "Mock output" in task.output_data.get("result", "")
    finally:
        manager.nodes._execute_single_task = original_exec
