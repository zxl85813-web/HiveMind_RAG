from datetime import datetime, timedelta
from typing import Dict, Any

from sqlmodel import select, func
from app.core.database import async_session_factory
from app.models.observability import LLMMetric
from app.core.config import settings
from app.core.logging import get_trace_logger

logger = get_trace_logger(__name__)

class BudgetService:
    """
    LLM 成本治理与预算审计服务 (M7.1 - ClawRouter 硬化)。
    职责:
    1. 统计日/月 Token 消耗金额。
    2. 对比阈值触发熔断或告警。
    3. 生成治理审计简报。
    """

    async def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前成本度量概览"""
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        async with async_session_factory() as session:
            # 1. 统计今日成本
            day_query = select(func.sum(LLMMetric.cost)).where(LLMMetric.created_at >= start_of_day)
            day_cost = (await session.exec(day_query)).first() or 0.0

            # 2. 统计当月成本
            month_query = select(func.sum(LLMMetric.cost)).where(LLMMetric.created_at >= start_of_month)
            month_cost = (await session.exec(month_query)).first() or 0.0

            # 3. 统计分模型消耗 (用于诊断)
            model_query = select(LLMMetric.model_name, func.sum(LLMMetric.cost)).group_by(LLMMetric.model_name)
            model_summary = (await session.exec(model_query)).all()

            return {
                "daily_cost": float(day_cost),
                "monthly_cost": float(month_cost),
                "daily_limit": settings.BUDGET_DAILY_LIMIT_USD,
                "monthly_limit": settings.BUDGET_MONTHLY_LIMIT_USD,
                "alert_threshold": settings.BUDGET_ALERT_THRESHOLD,
                "breakdown": {m: float(c) for m, c in model_summary}
            }

    async def check_alerts(self) -> Dict[str, Any]:
        """
        全量预算审计门禁。
        返回包含告警状态的字典。
        """
        metrics = await self.get_current_metrics()
        alerts = []
        is_exceeded = False

        # 每日检查
        day_ratio = metrics["daily_cost"] / max(metrics["daily_limit"], 0.01)
        if day_ratio >= 1.0:
            msg = f"🚨 [FATAL] Daily Budget EXCEEDED! Spent: ${metrics['daily_cost']:.2f} / Limit: ${metrics['daily_limit']:.2f}"
            logger.error(msg)
            alerts.append(msg)
            is_exceeded = True
        elif day_ratio >= metrics["alert_threshold"]:
            msg = f"⚠️ [WARN] Daily Budget Warning! Reached {day_ratio*100:.1f}% of limit."
            logger.warning(msg)
            alerts.append(msg)

        # 每月检查
        month_ratio = metrics["monthly_cost"] / max(metrics["monthly_limit"], 0.01)
        if month_ratio >= 1.0:
            msg = f"🚨 [FATAL] Monthly Budget EXCEEDED! Spent: ${metrics['monthly_cost']:.2f} / Limit: ${metrics['monthly_limit']:.2f}"
            logger.error(msg)
            alerts.append(msg)
            is_exceeded = True

        return {
            "status": "EXCEEDED" if is_exceeded else ("WARNING" if alerts else "OK"),
            "alerts": alerts,
            "metrics": metrics
        }

# 单例模式导出
budget_service = BudgetService()
