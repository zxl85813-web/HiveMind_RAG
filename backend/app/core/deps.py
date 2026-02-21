"""
依赖注入集合 — 所有 FastAPI Depends 函数的统一注册处。

用法:
    from app.core.deps import get_db, get_current_user, get_llm_router

路由中:
    @router.get("/")
    async def handler(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        ...

参见: REGISTRY.md > 后端 > 核心配置 > deps
"""

from app.core.database import get_db_session

# 统一别名 — 路由中直接 Depends(get_db)
get_db = get_db_session

# TODO: 完善以下依赖注入
# get_current_user — 从 security.py 引入
# get_llm_router — LLM 路由实例
# get_swarm — SwarmOrchestrator 实例
# get_memory — SharedMemoryManager 实例
# get_storage — 存储后端实例
