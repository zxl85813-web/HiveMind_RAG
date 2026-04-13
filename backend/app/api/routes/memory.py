from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from app.api.deps import get_current_user, get_db
from app.auth.permissions import Permission, require_permission
from app.core.graph_store import get_graph_store
from app.models.chat import User
from app.models.episodic import EpisodicMemory
from app.services.memory.memory_service import MemoryService, PersonalMemory, RoleMemory
from app.common.response import ApiResponse

router = APIRouter()


@router.get("/roles/{role_id}", dependencies=[Depends(require_permission(Permission.AGENT_VIEW))])
async def get_role_memory(role_id: str):
    """获取角色的群体记忆 (ARM-P1-1)."""
    mem_svc = MemoryService(user_id="system")
    return mem_svc._load_role_memory(role_id)


@router.put("/roles/{role_id}", dependencies=[Depends(require_permission(Permission.SYSTEM_CONFIG))])
async def update_role_memory(role_id: str, memory: RoleMemory):
    """更新角色的群体记忆 (ARM-P1-1)."""
    if memory.role_id != role_id:
        memory.role_id = role_id
    mem_svc = MemoryService(user_id="system")
    mem_svc.save_role_memory(memory)
    return {"status": "success", "memory": memory}


@router.get("/personal")
async def get_personal_memory(current_user: User = Depends(get_current_user)):
    """获取当前用户的个人记忆 (ARM-P1-2)."""
    mem_svc = MemoryService(user_id=str(current_user.id))
    return mem_svc._load_personal_memory()


@router.put("/personal")
async def update_personal_memory(memory: PersonalMemory, current_user: User = Depends(get_current_user)):
    """更新当前用户的个人记忆 (ARM-P1-2)."""
    if memory.user_id != str(current_user.id):
        memory.user_id = str(current_user.id)
    mem_svc = MemoryService(user_id=str(current_user.id))
    mem_svc.save_personal_memory(memory)
    return {"status": "success", "memory": memory}


# ── Episodic Memory (EP-010) ──────────────────────────────────────────────

@router.get("/episodes", response_model=ApiResponse[list[EpisodicMemory]])
async def list_episodes(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的情节记忆列表。"""
    stmt = (
        select(EpisodicMemory)
        .where(EpisodicMemory.user_id == str(current_user.id))
        .order_by(desc(EpisodicMemory.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    memories = res.scalars().all()
    return ApiResponse.ok(data=memories)


@router.get("/episodes/{episode_id}", response_model=ApiResponse[EpisodicMemory])
async def get_episode(
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单条情节记忆详情。"""
    episode = await db.get(EpisodicMemory, episode_id)
    if not episode or episode.user_id != str(current_user.id):
        return ApiResponse.error(message="Memory not found", code=404)
    return ApiResponse.ok(data=episode)


@router.delete("/episodes/{episode_id}")
async def delete_episode(
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除指定情节记忆。"""
    episode = await db.get(EpisodicMemory, episode_id)
    if not episode or episode.user_id != str(current_user.id):
        return ApiResponse.error(message="Memory not found", code=404)
    
    await db.delete(episode)
    await db.commit()
    return ApiResponse.ok(message="Episode deleted")


@router.get("/graph")
async def get_memory_graph(entities: list[str] = Query(None)):
    """
    Retrieve nodes and links for a set of entities to be rendered in the GraphVisualizer.
    """
    if not entities:
        return {"nodes": [], "links": []}

    store = get_graph_store()
    if not store or not store.driver:
        return {"nodes": [], "links": []}

    safe_entities = [str(e).strip() for e in entities if e.strip()]
    if not safe_entities:
        return {"nodes": [], "links": []}

    cypher = """
    MATCH (n)-[r]-(m)
     WHERE n.name IN $entities OR n.id IN $entities
       OR m.name IN $entities OR m.id IN $entities
     RETURN DISTINCT n {.*} as source, labels(n)[0] as s_label,
                          type(r) as rel,
                    m {.*} as target, labels(m)[0] as t_label
    LIMIT 50
    """

    results = await store.execute_query(cypher, {"entities": safe_entities})

    nodes_map = {}
    links = []

    for item in results:
        s = item["source"]
        t = item["target"]
        rel = item["rel"]

        s_id = s.get("id") or s.get("name")
        t_id = t.get("id") or t.get("name")

        if s_id not in nodes_map:
            nodes_map[s_id] = {
                "id": s_id,
                "name": s.get("name") or s_id,
                "label": item.get("s_label", "Entity"),
                "color": "#06D6A0" if item.get("s_label") == "Concept" else "#118AB2",
            }

        if t_id not in nodes_map:
            nodes_map[t_id] = {
                "id": t_id,
                "name": t.get("name") or t_id,
                "label": item.get("t_label", "Entity"),
                "color": "#06D6A0" if item.get("t_label") == "Concept" else "#118AB2",
            }

        links.append({"source": s_id, "target": t_id, "type": rel})

    return {"nodes": list(nodes_map.values()), "links": links}
