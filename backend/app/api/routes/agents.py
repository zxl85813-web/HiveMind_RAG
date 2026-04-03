"""
Agent management & monitoring endpoints.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.swarm import SwarmOrchestrator
from app.batch.engine import JobManager
from app.batch.models import TaskStep, TaskUnit
from app.common.response import ApiResponse
from app.models.agents import ReflectionSignalType
from app.services.rag_gateway import RAGGateway

router = APIRouter()

# Global Swarm & Job Manager (Lazy Loading)
_swarm_instance = None
_job_manager_instance = None

def get_swarm():
    global _swarm_instance
    if _swarm_instance is None:
        _swarm_instance = SwarmOrchestrator()
    return _swarm_instance

def get_job_manager():
    global _job_manager_instance
    if _job_manager_instance is None:
        _job_manager_instance = JobManager(swarm=get_swarm())
    return _job_manager_instance


# --- Request Models ---


class CreateBatchJobRequest(BaseModel):
    name: str
    description: str = ""
    tasks: list[dict]  # Simple list of tasks for demo
    max_concurrency: int = 3
    kb_ids: list[str] = []


class SwarmChatRequest(BaseModel):
    message: str
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kb_ids: list[str] = []
    parent_message_id: str | None = None


class DevRAGSearchRequest(BaseModel):
    query: str
    kb_ids: list[str] = []
    top_k: int = 5
    strategy: str = "hybrid"
    include_graph: bool = True


# --- Endpoints ---


@router.post("/batch/jobs")
async def create_batch_job(request: CreateBatchJobRequest, background_tasks: BackgroundTasks):
    """Create and start a new batch job."""
    task_units = []
    for t_data in request.tasks:
        task_units.append(
            TaskUnit(
                id=t_data.get("id") or str(uuid.uuid4()),  # Allow custom ID for DAG linking
                name=t_data.get("name", "Untitled Task"),
                input_data=t_data.get("input_data", {}),
                depends_on=t_data.get("depends_on", []),
                steps=[TaskStep(name="default_step", agent_name="auto")],
            )
        )

    job = await get_job_manager().create_job(
        name=request.name,
        tasks=task_units,
    )
    job.max_concurrency = request.max_concurrency

    # Start in background using LangGraph
    background_tasks.add_task(get_job_manager().start_job, job.id, job)

    return {"job_id": job.id, "status": "created"}


@router.get("/batch/jobs")
async def list_batch_jobs():
    """List all batch jobs."""
    return get_job_manager().list_jobs()


@router.get("/batch/jobs/{job_id}")
async def get_batch_job_status(job_id: str):
    """Get detailed status of a specific batch job."""
    job = get_job_manager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Return full job object (Pydantic serializes to JSON)
    return job


@router.post("/batch/jobs/{job_id}/cancel")
async def cancel_batch_job(job_id: str):
    """Cancel a running batch job."""
    await get_job_manager().cancel_job(job_id)
    return {"status": "cancelled"}


@router.get("/swarm/reflections")
async def get_swarm_reflections(
    limit: int = 20,
    signal_type: ReflectionSignalType | None = None,
    match_key: str | None = None,
):
    """Get recent reflections from the agent swarm."""
    swarm = get_swarm()
    memory_manager = getattr(swarm, "memory", None)
    if not memory_manager:
        return []
    reflections = await memory_manager.get_reflections(limit=limit, signal_type=signal_type, match_key=match_key)
    return ApiResponse.ok(data=reflections)


@router.get("/swarm/reflections/matches")
async def get_swarm_reflection_matches(limit: int = 10):
    """Get suggested GAP -> INSIGHT pairings (exact key + semantic overlap)."""
    swarm = get_swarm()
    memory_manager = getattr(swarm, "memory", None)
    if not memory_manager:
        return ApiResponse.ok(data=[])
    matches = await memory_manager.suggest_gap_matches(limit=limit)
    return ApiResponse.ok(data=matches)


@router.get("/swarm/agents")
async def get_swarm_agents():
    """Get all registered agents in the swarm."""
    swarm = get_swarm()
    agents = swarm.get_agents()
    return ApiResponse.ok(
        data=[
            {
                "name": a.name,
                "description": a.description,
                "status": "idle",  # Default status for now
                "icon": a.icon if hasattr(a, "icon") else "🤖",
            }
            for a in agents.values()
        ]
    )


@router.get("/swarm/stats")
async def get_swarm_stats():
    """Get high-level swarm statistics."""
    swarm = get_swarm()
    agents = swarm.get_agents()
    memory_manager = getattr(swarm, "memory", None)
    reflections_count = 0
    todos_count = 0
    if memory_manager:
        reflections = await memory_manager.get_reflections(limit=1000)
        reflections_count = len(reflections)
        todos = await memory_manager.get_todos()
        todos_count = len(todos)

    return ApiResponse.ok(
        data={
            "active_agents": len(agents),
            "today_requests": 0,  # TODO: Track this
            "shared_todos": todos_count,
            "reflection_logs": reflections_count,
        }
    )


@router.get("/swarm/todos")
async def get_swarm_todos():
    """Get the communal TODO list from shared memory."""
    swarm = get_swarm()
    memory_manager = getattr(swarm, "memory", None)
    if not memory_manager:
        return ApiResponse.ok(data=[])
    todos = await memory_manager.get_todos()
    return ApiResponse.ok(data=todos)


@router.get("/swarm/traces")
async def get_swarm_traces():
    """Get the live execution DAG trace."""
    swarm = get_swarm()
    memory_manager = getattr(swarm, "memory", None)
    if not memory_manager:
        return ApiResponse.ok(data={"nodes": [], "links": []})
    traces = await memory_manager.get_traces()
    return ApiResponse.ok(data=traces)


@router.post("/swarm/chat")
async def swarm_chat_stream(
    request: SwarmChatRequest,
    user_id: str | None = None  # TODO: Get from deps.get_current_user
):
    """
    Streaming entry point for the Agent Swarm Chat.
    Yields LangGraph node updates and AI message chunks as Server-Sent Events (SSE).
    """
    context = {
        "user_id": user_id,
        "knowledge_base_ids": request.kb_ids,
        "language": "zh-CN",
    }
    swarm = get_swarm()

    async def event_generator():
        try:
            # yield initial signal
            yield f"data: {json.dumps({'event': 'start', 'conversation_id': request.conversation_id})}\n\n"

            async for update in swarm.invoke_stream(
                user_message=request.message,
                context=context,
                conversation_id=request.conversation_id
            ):
                # LangGraph 2.0 output is a dict of {node_name: state_diff}
                for node_name, state_diff in update.items():
                    # Send node status update
                    yield f"data: {json.dumps({'event': 'node_start', 'node': node_name})}\n\n"

                    # Extract thought logs or status updates if present
                    thought = state_diff.get("thought_log") or state_diff.get("status_update")
                    if thought:
                        yield f"data: {json.dumps({'event': 'thought', 'content': thought})}\n\n"

                    # Extract messages if present in diff
                    msgs = state_diff.get("messages", [])
                    for m in msgs:
                        # Only stream AI messages content for UI
                        if hasattr(m, "content") and m.type == "ai":
                             yield f"data: {json.dumps({'event': 'delta', 'content': m.content})}\n\n"

                    yield f"data: {json.dumps({'event': 'node_end', 'node': node_name})}\n\n"

            yield f"data: {json.dumps({'event': 'done'})}\n\n"
        except Exception as e:
            logger.error(f"Swarm Stream Error: {e}")
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/swarm/dev-rag/search")
async def search_swarm_dev_rag(request: DevRAGSearchRequest):
    """
    Development-facing RAG endpoint for agents.
    Intended for code/doc retrieval workflows backed by vector + graph stores.
    """
    gateway = RAGGateway()
    result = await gateway.retrieve_for_development(
        query=request.query,
        kb_ids=request.kb_ids,
        top_k=request.top_k,
        strategy=request.strategy,
        include_graph=request.include_graph,
    )
    return ApiResponse.ok(data=result)


@router.get("/mcp/status")
async def get_mcp_status():
    """Get status of all configured MCP servers."""
    swarm = get_swarm()
    if not hasattr(swarm, "mcp"):
        return ApiResponse.ok(data={})

    status = await swarm.mcp.health_check()

    # We want to return more detailed info
    result = []
    for name, is_connected in status.items():
        config = swarm.mcp._servers.get(name, {})
        result.append(
            {
                "name": name,
                "status": "connected" if is_connected else "disconnected",
                "type": config.get("type", "unknown"),
                "command": config.get("command", ""),
                "args": config.get("args", []),
            }
        )
    return ApiResponse.ok(data=result)


@router.get("/mcp/tools")
async def get_mcp_tools():
    """Get all tools loaded from MCP servers."""
    swarm = get_swarm()
    if not hasattr(swarm, "mcp"):
        return ApiResponse.ok(data=[])

    tools = swarm.mcp.get_tools()

    result = []
    for t in tools:
        if not hasattr(t, "name"):
            continue
        result.append(
            {
                "name": t.name,
                "description": getattr(t, "description", ""),
            }
        )

    return ApiResponse.ok(data=result)


@router.get("/skills")
async def get_skills():
    """Get all registered skills from SkillRegistry."""
    # Assuming SkillRegistry is global or we can parse it from directories
    # For now, let's just use the file system since it's dynamic
    from pathlib import Path

    import yaml

    skills_dir = Path("app/skills")
    if not skills_dir.exists():
        return ApiResponse.ok(data=[])

    skills = []
    for d in skills_dir.iterdir():
        if d.is_dir() and not d.name.startswith("__"):
            skill_md = d / "SKILL.md"
            if skill_md.exists():
                # Extract basic info
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    if content.startswith("---"):
                        frontmatter = content.split("---")[1]
                        meta = yaml.safe_load(frontmatter)
                        skills.append(
                            {
                                "name": meta.get("name", d.name),
                                "description": meta.get("description", ""),
                                "version": meta.get("version", "0.1.0"),
                                "status": "active",
                            }
                        )
                except Exception:
                    skills.append({"name": d.name, "description": "Failed to parse SKILL.md", "status": "error"})

    return ApiResponse.ok(data=skills)
