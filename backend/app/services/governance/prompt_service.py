from typing import Dict, Any, Optional
from sqlmodel import select
from app.core.database import async_session_factory
from app.models.governance import PromptDefinition, PromptStatus
from app.core.logging import get_trace_logger

logger = get_trace_logger(__name__)

class PromptService:
    """
    Prompt 集中化治理与版本分发服务 (P0 - Prompt Governance)。
    职责:
    1. 动态加载最新的 Prompt 模版。
    2. 提供 A/B 版本测试分流接口 (TBD)。
    3. 支持生产环境热修复 Prompt 而无需重启后端。
    """
    
    _cache: Dict[str, PromptDefinition] = {}

    async def get_prompt(self, slug: str, version: Optional[str] = None) -> str:
        """
        获取指定 slug 的 Prompt。
        优先从缓存获取，缓存失效后查询数据库。
        """
        cache_key = f"{slug}:{version or 'current'}"
        if cache_key in self._cache:
            return self._cache[cache_key].content

        async with async_session_factory() as session:
            if version:
                statement = select(PromptDefinition).where(
                    PromptDefinition.slug == slug,
                    PromptDefinition.version == version
                )
            else:
                statement = select(PromptDefinition).where(
                    PromptDefinition.slug == slug,
                    PromptDefinition.is_current == True
                )
            
            result = (await session.exec(statement)).first()
            
            if result:
                self._cache[cache_key] = result
                return result.content
            
            # Fallback (治理初期，如果 DB 没数据，抛出异常或记录错误)
            logger.error(f"❌ [PromptGov] Prompt not found in registry: {slug} (version={version})")
            return ""

    async def register_prompt(self, 
                                slug: str, 
                                version: str, 
                                content: str, 
                                is_current: bool = False,
                                recommended_model: str = "gpt-4o",
                                change_log: str = "Initial version") -> PromptDefinition:
        """
        在注册表中登记或更新 Prompt 版本。
        """
        async with async_session_factory() as session:
            # 如果设置为当前版本，取消该 slug 其他版本的主版本标记
            if is_current:
                old_currents = (await session.exec(
                    select(PromptDefinition).where(
                        PromptDefinition.slug == slug, 
                        PromptDefinition.is_current == True
                    )
                )).all()
                for old in old_currents:
                    old.is_current = False
                    session.add(old)

            new_prompt = PromptDefinition(
                slug=slug,
                version=version,
                content=content,
                is_current=is_current,
                recommended_model=recommended_model,
                status=PromptStatus.ACTIVE,
                change_log=change_log
            )
            session.add(new_prompt)
            await session.commit()
            await session.refresh(new_prompt)
            
            # 清理缓存
            self._cache.pop(f"{slug}:current", None)
            self._cache.pop(f"{slug}:{version}", None)
            
            logger.info(f"✅ [PromptGov] Registered new prompt: {slug} v{version}")
            return new_prompt

    def invalidate_cache(self, slug: Optional[str] = None):
        if slug:
            keys_to_del = [k for k in self._cache if k.startswith(f"{slug}:")]
            for k in keys_to_del:
                self._cache.pop(k, None)
        else:
            self._cache.clear()

prompt_service = PromptService()
