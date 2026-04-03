from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlmodel import select, col, func
from app.core.database import async_session_factory
from app.models.knowledge import Document
from app.core.logging import get_trace_logger

logger = get_trace_logger(__name__)

class KnowledgeFreshnessService:
    """
    RAG 知识状态治理服务 (TASK-GOV-003)。
    职责:
    1. 识别并标记过期的陈旧文档。
    2. 管理文档审核周期 (Review Lifecycle)。
    3. 防止 RAG 检索被过期知识污染。
    """

    async def get_freshness_report(self) -> Dict[str, Any]:
        """获取全系统知识新鲜度报告"""
        now = datetime.utcnow()
        async with async_session_factory() as session:
            all_documents = (await session.exec(select(Document))).all()
            
            total = len(all_documents)
            expired = [d for d in all_documents if d.expiry_date and d.expiry_date < now]
            stale = [d for d in all_documents if d.next_review_at and d.next_review_at < now]
            
            return {
                "total_documents": total,
                "expired_count": len(expired),
                "stale_count": len(stale),
                "healthy_count": total - len(expired) - len(stale),
                "expired_details": [
                    {"id": d.id, "filename": d.filename, "expiry": d.expiry_date}
                    for d in expired
                ]
            }

    async def set_default_freshness(self, months: int = 6):
        """
        为所有未设置过期时间的文档设置默认新鲜度阈值 (例如 6 个月)。
        这是一种“治理补课”操作。
        """
        now = datetime.utcnow()
        default_expiry = now + timedelta(days=30 * months)
        
        async with async_session_factory() as session:
            stmt = select(Document).where(Document.expiry_date == None)
            targets = (await session.exec(stmt)).all()
            
            for doc in targets:
                doc.expiry_date = default_expiry
                doc.next_review_at = now + timedelta(days=30 * (months // 2)) # 中间点审核
                session.add(doc)
            
            await session.commit()
            logger.info(f"🛡️ [FreshnessGov] Applied default freshness to {len(targets)} documents.")
            return len(targets)

knowledge_freshness_service = KnowledgeFreshnessService()
