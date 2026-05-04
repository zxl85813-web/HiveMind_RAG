"""
Agent management & monitoring endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Query
import uuid
from loguru import logger
from pydantic import BaseModel

from app.batch.controller import BatchController
from app.batch.models import TaskUnit, TaskStep, BatchJob, BatchStatus
from app.batch.engine import JobManager
from app.agents.swarm import SwarmOrchestrator
from app.common.response import ApiResponse
from app.core.config import settings

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


class McpServerUpsertRequest(BaseModel):
    """Add or update an MCP server entry."""
    name: str
    type: str = "stdio"
    command: str
    args: list[str] = []
    env: dict[str, str] | None = None


class AgentUpsertRequest(BaseModel):
    """Create or update a runtime agent."""
    name: str
    description: str = ""
    skills: list[str] = []
    model_hint: str | None = None  # "fast" | "balanced" | "reasoning"


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

    def _tool_names(tools: list) -> list[str]:
        """Extract tool names from a list of LangChain tool objects or strings."""
        names = []
        for t in tools:
            if isinstance(t, str):
                names.append(t)
            elif hasattr(t, "name"):
                names.append(t.name)
            elif hasattr(t, "__name__"):
                names.append(t.__name__)
        return names

    return ApiResponse.ok(data=[
        {
            "name": a.name,
            "description": a.description,
            "status": "idle",  # Default status for now
            "icon": a.icon if hasattr(a, 'icon') else "🤖",
            "skills": a.skills if hasattr(a, 'skills') else [],
            "tools": _tool_names(a.tools) if hasattr(a, 'tools') else [],
            "model_hint": a.model_hint if hasattr(a, 'model_hint') else None,
            "built_in": getattr(a, 'built_in', False),
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


@router.get("/swarm/topology")
async def get_swarm_topology():
    """
    Get the Agent-Skill-Tool capability topology graph for visualization.

    Returns a graph with three node types:
      - agent  → each registered Agent
      - skill  → each Skill bound to at least one Agent
      - tool   → each MCP/native Tool bound to at least one Agent

    Links express:
      - agent → skill  (rel: "uses")
      - agent → tool   (rel: "has_tool")
    """
    agents = _swarm.get_agents()

    def _tool_names(tools: list) -> list[str]:
        names: list[str] = []
        for t in tools:
            if isinstance(t, str):
                names.append(t)
            elif hasattr(t, "name"):
                names.append(t.name)
            elif hasattr(t, "__name__"):
                names.append(t.__name__)
        return names

    nodes: list[dict] = []
    links: list[dict] = []
    seen_skills: set[str] = set()
    seen_tools: set[str] = set()

    for a in agents.values():
        agent_id = f"agent:{a.name}"
        nodes.append({
            "id": agent_id,
            "label": a.name,
            "type": "agent",
            "icon": a.icon if hasattr(a, "icon") else "🤖",
            "model_hint": a.model_hint if hasattr(a, "model_hint") else None,
        })

        for skill in (a.skills or []):
            skill_id = f"skill:{skill}"
            if skill not in seen_skills:
                nodes.append({"id": skill_id, "label": skill, "type": "skill"})
                seen_skills.add(skill)
            links.append({"source": agent_id, "target": skill_id, "rel": "uses"})

        for tool_name in _tool_names(a.tools or []):
            tool_id = f"tool:{tool_name}"
            if tool_name not in seen_tools:
                nodes.append({"id": tool_id, "label": tool_name, "type": "tool"})
                seen_tools.add(tool_name)
            links.append({"source": agent_id, "target": tool_id, "rel": "has_tool"})

    return ApiResponse.ok(data={"nodes": nodes, "links": links})


# ============================================================
#  MCP Server CRUD (writes mcp_servers.json + hot reconnect)
# ============================================================

def _ensure_mcp() -> "MCPManager":  # type: ignore[name-defined]
    if not hasattr(_swarm, "mcp"):
        raise HTTPException(status_code=500, detail="MCP manager is not initialized")
    return _swarm.mcp


@router.post("/mcp/servers")
async def create_or_update_mcp_server(request: McpServerUpsertRequest):
    """Add or replace an MCP server config and trigger a reconnect."""
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Server name is required")
    if not request.command.strip():
        raise HTTPException(status_code=400, detail="Command is required")

    mcp = _ensure_mcp()
    config: dict = {
        "type": request.type,
        "command": request.command,
        "args": request.args or [],
    }
    if request.env:
        config["env"] = request.env

    mcp.update_server_config(request.name, config)
    try:
        mcp.persist_config(settings.MCP_SERVERS_CONFIG_PATH, mcp.get_servers_config())
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to persist MCP config: {e}")
        raise HTTPException(status_code=500, detail=f"Persist failed: {e}")

    try:
        await mcp.reconnect_all(settings.MCP_SERVERS_CONFIG_PATH)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Reconnect failed: {e}")
        # Persistence already happened; surface the error but keep config

    return ApiResponse.ok(data={"name": request.name, "saved": True})


@router.delete("/mcp/servers/{name}")
async def delete_mcp_server(name: str):
    """Remove an MCP server config and trigger a reconnect."""
    mcp = _ensure_mcp()
    existed = mcp.remove_server_config(name)
    if not existed:
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")

    try:
        mcp.persist_config(settings.MCP_SERVERS_CONFIG_PATH, mcp.get_servers_config())
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to persist MCP config: {e}")
        raise HTTPException(status_code=500, detail=f"Persist failed: {e}")

    try:
        await mcp.reconnect_all(settings.MCP_SERVERS_CONFIG_PATH)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Reconnect failed: {e}")

    return ApiResponse.ok(data={"name": name, "deleted": True})


@router.post("/mcp/reconnect")
async def reconnect_all_mcp_servers():
    """Force a full disconnect/reconnect cycle on all MCP servers."""
    mcp = _ensure_mcp()
    try:
        await mcp.reconnect_all(settings.MCP_SERVERS_CONFIG_PATH)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Reconnect failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reconnect failed: {e}")
    return ApiResponse.ok(data={"reconnected": True})


# ============================================================
#  Agent CRUD (runtime add/edit/delete with persistence)
# ============================================================

@router.post("/swarm/agents")
async def upsert_swarm_agent(request: AgentUpsertRequest):
    """
    Create or update a runtime agent.
    Built-in agents (registered in main.py) cannot be modified via this endpoint.
    """
    from app.agents.swarm import AgentDefinition

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Agent name is required")
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Description is required (used by Supervisor for routing)")

    existing = _swarm.get_agents().get(name)
    if existing and getattr(existing, "built_in", False):
        raise HTTPException(status_code=403, detail=f"Built-in agent '{name}' cannot be modified")

    _swarm.register_agent(AgentDefinition(
        name=name,
        description=request.description.strip(),
        skills=request.skills or [],
        model_hint=request.model_hint,
        built_in=False,
    ))

    try:
        _swarm.persist_custom_agents()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to persist custom agents: {e}")
        raise HTTPException(status_code=500, detail=f"Persist failed: {e}")

    return ApiResponse.ok(data={"name": name, "saved": True})


@router.delete("/swarm/agents/{name}")
async def delete_swarm_agent(name: str):
    """Delete a runtime agent. Built-in agents cannot be deleted."""
    existing = _swarm.get_agents().get(name)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    if getattr(existing, "built_in", False):
        raise HTTPException(status_code=403, detail=f"Built-in agent '{name}' cannot be deleted")

    _swarm.unregister_agent(name)
    try:
        _swarm.persist_custom_agents()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to persist custom agents: {e}")
        raise HTTPException(status_code=500, detail=f"Persist failed: {e}")

    return ApiResponse.ok(data={"name": name, "deleted": True})


# ============================================================
#  Skill Lifecycle (install / uninstall / toggle / reload)
# ============================================================

@router.post("/skills/upload")
async def install_skill_zip(
    file: UploadFile = File(..., description="ZIP archive containing a top-level SKILL folder"),
    overwrite: bool = Query(False, description="Overwrite existing skill with same folder name"),
):
    """
    Install a skill from a ZIP archive.

    The ZIP must contain exactly one top-level folder, and that folder
    must contain a SKILL.md file. Optional ``tools.py`` provides callable
    tools.
    """
    from app.skills.registry import get_skill_registry

    if not file.filename or not file.filename.lower().endswith((".zip",)):
        raise HTTPException(status_code=400, detail="A .zip file is required")
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    registry = get_skill_registry()
    try:
        result = await registry.install_from_zip(payload, overwrite=overwrite)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"Skill install failed: {e}")
        raise HTTPException(status_code=500, detail=f"Install failed: {e}")

    return ApiResponse.ok(data=result)


@router.delete("/skills/{name}")
async def uninstall_skill(name: str, delete_files: bool = Query(True)):
    """Uninstall a skill. By default also deletes its directory on disk."""
    from app.skills.registry import get_skill_registry

    registry = get_skill_registry()
    if not registry.list_skills():
        await registry.load_all()
    if not registry.uninstall(name, delete_files=delete_files):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return ApiResponse.ok(data={"name": name, "deleted": True, "files_removed": delete_files})


@router.post("/skills/{name}/toggle")
async def toggle_skill(name: str, enabled: bool = Query(...)):
    """Enable or disable a skill (in-memory only, persists across reload via SKILL.md)."""
    from app.skills.registry import get_skill_registry

    registry = get_skill_registry()
    if not registry.list_skills():
        await registry.load_all()
    if not registry.toggle(name, enabled):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return ApiResponse.ok(data={"name": name, "enabled": enabled})


@router.post("/skills/reload")
async def reload_skills():
    """Force a re-scan of the skills directory."""
    from app.skills.registry import get_skill_registry

    registry = get_skill_registry()
    count = await registry.reload_async()
    return ApiResponse.ok(data={"reloaded": True, "skill_count": count})
