from fastapi import APIRouter, Depends, BackgroundTasks
from typing import Dict, Any, List
from sqlalchemy import text
from sqlmodel import select

from app.api.deps import get_current_admin
from app.core.database import async_session_factory
from app.sdk.core.logging import get_trace_logger

router = APIRouter()
logger = get_trace_logger("api.performance")

@router.get("/db/stats")
async def get_db_performance_stats(
    current_user: Any = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Get real-time database performance metrics from PostgreSQL system views.
    """
    async with async_session_factory() as session:
        # 1. Lock Contentions
        lock_query = text("""
            SELECT 
                count(*) as total_locks,
                count(*) FILTER (WHERE NOT granted) as waiting_locks
            FROM pg_locks;
        """)
        
        # 2. Transaction Activity
        activity_query = text("""
            SELECT 
                count(*) FILTER (WHERE state = 'active') as active_xacts,
                count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_xact,
                avg(now() - query_start) FILTER (WHERE state = 'active') as avg_query_duration
            FROM pg_stat_activity;
        """)
        
        # 3. Cache Hit Ratio
        cache_query = text("""
            SELECT 
                sum(heap_blks_read) as heap_read,
                sum(heap_blks_hit) as heap_hit,
                (sum(heap_hit) / (sum(heap_hit) + sum(heap_read) + 0.000001)) * 100 as hit_ratio
            FROM pg_statio_user_tables;
        """)

        locks = (await session.execute(lock_query)).mappings().first()
        activity = (await session.execute(activity_query)).mappings().first()
        cache = (await session.execute(cache_query)).mappings().first()

        return {
            "locks": {
                "total": locks["total_locks"],
                "waiting": locks["waiting_locks"]
            },
            "activity": {
                "active": activity["active_xacts"],
                "idle_in_xact": activity["idle_in_xact"],
                "avg_duration_ms": activity["avg_query_duration"].total_seconds() * 1000 if activity["avg_query_duration"] else 0
            },
            "cache": {
                "hit_ratio": float(cache["hit_ratio"])
            },
            "es": await get_es_metrics()
        }

async def get_es_metrics() -> Dict[str, Any]:
    """Fetch basic ES health and performance metrics."""
    try:
        from app.core.vector_store import get_vector_store, ElasticVectorStore
        store = get_vector_store()
        if not isinstance(store, ElasticVectorStore):
            return {"status": "inactive", "reason": "Not using ES"}
            
        health = await store.client.cluster.health()
        stats = await store.client.indices.stats()
        
        return {
            "status": health["status"],
            "indices_count": len(stats["indices"]),
            "total_docs": stats["_all"]["total"]["docs"]["count"],
            "store_size_gb": round(stats["_all"]["total"]["store"]["size_in_bytes"] / (1024**3), 2),
            "search_time_ms": stats["_all"]["total"]["search"]["query_time_in_millis"]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/db/deadlocks")
async def get_deadlock_history(
    current_user: Any = Depends(get_current_admin)
) -> List[Dict[str, Any]]:
    """
    Check for detected deadlocks in the PostgreSQL logs (if configured) or stats.
    """
    async with async_session_factory() as session:
        # PostgreSQL doesn't store a 'deadlock history' table by default, 
        # but we can check pg_stat_database for the counter.
        query = text("""
            SELECT datname, deadlocks, conflicts, blks_read, blks_hit 
            FROM pg_stat_database 
            WHERE datname = current_database();
        """)
        res = await session.execute(query)
        return [dict(row) for row in res.mappings()]

@router.post("/db/drill/deadlock")
async def trigger_deadlock_drill(
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_admin)
):
    """
    Trigger the AB-BA deadlock drill in the background to verify DB self-healing.
    """
    from scripts.db_deadlock_drill import trigger_deadlock_probe
    background_tasks.add_task(trigger_deadlock_probe)
    return {"message": "Deadlock drill triggered in background", "status": "running"}
