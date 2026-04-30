"""
Agent management & monitoring endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
import uuid
from loguru import logger
from pydantic import BaseModel

from app.batch.controller import BatchController
from app.batch.models import TaskUnit, TaskStep, BatchJob, BatchStatus
from app.batch.engine import JobManager
from app.agents.swarm import SwarmOrchestrator
from app.common.response import ApiResponse

router = APIRouter()

# Global Swarm & Job Manager (Singletons)
_swarm = SwarmOrchestrator()
_job_manager = JobManager(swarm=_swarm)


# --- Request Models ---

class CreateBatchJobRequest(BaseModel):
    name: str
    description: str = ""
    tasks: list[dict]  # Simple list of tasks for demo
    max_concurrency: int = 3


# --- Endpoints ---

@router.post("/batch/jobs")
async def create_batch_job(request: CreateBatchJobRequest, background_tasks: BackgroundTasks):
    """Create and start a new batch job."""
    task_units = []
    for t_data in request.tasks:
        task_units.append(TaskUnit(
            id=t_data.get("id") or str(uuid.uuid4()), # Allow custom ID for DAG linking
            name=t_data.get("name", "Untitled Task"),
            input_data=t_data.get("input_data", {}),
            depends_on=t_data.get("depends_on", []),
            steps=[TaskStep(name="default_step", agent_name="auto")],
        ))
        
    job = await _job_manager.create_job(
        name=request.name,
        tasks=task_units,
    )
    job.max_concurrency = request.max_concurrency
    
    # Start in background using LangGraph
    background_tasks.add_task(_job_manager.start_job, job.id, job)
    
    return {"job_id": job.id, "status": "created"}


@router.get("/batch/jobs")
async def list_batch_jobs():
    """List all batch jobs."""
    return _job_manager.list_jobs()


@router.get("/batch/jobs/{job_id}")
async def get_batch_job_status(job_id: str):
    """Get detailed status of a specific batch job."""
    job = _job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Return full job object (Pydantic serializes to JSON)
    return job

@router.post("/batch/jobs/{job_id}/cancel")
async def cancel_batch_job(job_id: str):
    """Cancel a running batch job."""
    await _job_manager.cancel_job(job_id)
    return {"status": "cancelled"}

@router.get("/swarm/reflections")
async def get_swarm_reflections(limit: int = 20):
    """Get recent reflections from the agent swarm."""
    memory_manager = getattr(_swarm, "memory", None)
    if not memory_manager:
        return []
    reflections = await memory_manager.get_reflections(limit=limit)
    return ApiResponse.ok(data=reflections)

@router.get("/swarm/agents")
async def get_swarm_agents():
    """Get all registered agents in the swarm."""
    agents = _swarm.get_agents()
    return ApiResponse.ok(data=[
        {
            "name": a.name,
            "description": a.description,
            "status": "idle",  # Default status for now
            "icon": a.icon if hasattr(a, 'icon') else "🤖"
        }
        for a in agents.values()
    ])

@router.get("/swarm/stats")
async def get_swarm_stats():
    """Get high-level swarm statistics."""
    agents = _swarm.get_agents()
    memory_manager = getattr(_swarm, "memory", None)
    reflections_count = 0
    todos_count = 0
    if memory_manager:
        reflections = await memory_manager.get_reflections(limit=1000)
        reflections_count = len(reflections)
        todos = await memory_manager.get_todos()
        todos_count = len(todos)
        
    return ApiResponse.ok(data={
        "active_agents": len(agents),
        "today_requests": 0, # TODO: Track this
        "shared_todos": todos_count,
        "reflection_logs": reflections_count
    })

@router.get("/swarm/todos")
async def get_swarm_todos():
    """Get the communal TODO list from shared memory."""
    memory_manager = getattr(_swarm, "memory", None)
    if not memory_manager:
        return ApiResponse.ok(data=[])
    todos = await memory_manager.get_todos()
    return ApiResponse.ok(data=todos)

@router.get("/swarm/traces")
async def get_swarm_traces():
    """Get the live execution DAG trace."""
    memory_manager = getattr(_swarm, "memory", None)
    if not memory_manager:
        return ApiResponse.ok(data={"nodes": [], "links": []})
    traces = await memory_manager.get_traces()
    return ApiResponse.ok(data=traces)

@router.get("/mcp/status")
async def get_mcp_status():
    """Get status of all configured MCP servers."""
    if not hasattr(_swarm, "mcp"):
        return ApiResponse.ok(data={})
        
    status = await _swarm.mcp.health_check()
    
    # We want to return more detailed info
    result = []
    for name, is_connected in status.items():
        config = _swarm.mcp._servers.get(name, {})
        result.append({
            "name": name,
            "status": "connected" if is_connected else "disconnected",
            "type": config.get("type", "unknown"),
            "command": config.get("command", ""),
            "args": config.get("args", []),
        })
    return ApiResponse.ok(data=result)

@router.get("/mcp/tools")
async def get_mcp_tools():
    """Get all tools loaded from MCP servers."""
    if not hasattr(_swarm, "mcp"):
        return ApiResponse.ok(data=[])
        
    tools = _swarm.mcp.get_tools()
    
    result = []
    for t in tools:
        if not hasattr(t, "name"):
            continue
        result.append({
            "name": t.name,
            "description": getattr(t, "description", ""),
        })
        
    return ApiResponse.ok(data=result)

@router.get("/skills")
async def get_skills(query: str | None = None, limit: int = 50):
    """List all registered skills (Tier 1 catalog)."""
    from app.skills.registry import get_skill_registry

    registry = get_skill_registry()
    if not registry.list_skills():
        await registry.load_all()
    return ApiResponse.ok(data=registry.catalog(query=query, limit=limit))


@router.get("/skills/{name}")
async def get_skill_detail(name: str):
    """Return Tier 2 detail for a single skill (full SKILL.md + tools)."""
    from app.skills.registry import get_skill_registry

    registry = get_skill_registry()
    if not registry.list_skills():
        await registry.load_all()
    detail = registry.inspect(name)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return ApiResponse.ok(data=detail)
