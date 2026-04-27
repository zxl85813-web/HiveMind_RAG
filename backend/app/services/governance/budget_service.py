from datetime import datetime
from typing import Any, Dict

from sqlmodel import func, select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import get_trace_logger
from app.models.observability import LLMMetric

logger = get_trace_logger(__name__)


class BudgetService:
    """
    LLM 成本治理与预算审计服务 (M7.1 - ClawRouter 硬化)。
    职责:
    1. 统计日/月 Token 消耗金额（区分 cache hit/miss 真实成本）。
    2. 对比阈值触发熔断或告警。
    3. 生成治理审计简报，包含缓存节省统计。
    """

    async def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前成本度量概览（含缓存节省数据）。"""
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        async with async_session_factory() as session:
            # 1. 今日成本
            day_cost = (
                await session.exec(
                    select(func.sum(LLMMetric.cost)).where(LLMMetric.created_at >= start_of_day)
                )
            ).first() or 0.0

            # 2. 当月成本
            month_cost = (
                await session.exec(
                    select(func.sum(LLMMetric.cost)).where(LLMMetric.created_at >= start_of_month)
                )
            ).first() or 0.0

            # 3. 今日缓存节省
            day_savings = (
                await session.exec(
                    select(func.sum(LLMMetric.cache_savings_usd)).where(
                        LLMMetric.created_at >= start_of_day
                    )
                )
            ).first() or 0.0

            # 4. 当月缓存节省
            month_savings = (
                await session.exec(
                    select(func.sum(LLMMetric.cache_savings_usd)).where(
                        LLMMetric.created_at >= start_of_month
                    )
                )
            ).first() or 0.0

            # 5. 今日缓存命中 token 数（用于计算命中率）
            day_cache_hit_tokens = (
                await session.exec(
                    select(func.sum(LLMMetric.tokens_cache_hit)).where(
                        LLMMetric.created_at >= start_of_day
                    )
                )
            ).first() or 0

            day_total_input_tokens = (
                await session.exec(
                    select(func.sum(LLMMetric.tokens_input)).where(
                        LLMMetric.created_at >= start_of_day
                    )
                )
            ).first() or 0

            # 6. 分模型消耗（含节省）
            model_rows = (
                await session.exec(
                    select(
                        LLMMetric.model_name,
                        func.sum(LLMMetric.cost).label("cost"),
                        func.sum(LLMMetric.cache_savings_usd).label("savings"),
                        func.sum(LLMMetric.tokens_cache_hit).label("cache_hit_tokens"),
                        func.sum(LLMMetric.tokens_input).label("total_input_tokens"),
                    ).group_by(LLMMetric.model_name)
                )
            ).all()

        # 缓存命中率（今日）
        cache_hit_rate = (
            round(day_cache_hit_tokens / day_total_input_tokens, 4)
            if day_total_input_tokens > 0
            else 0.0
        )

        return {
            "daily_cost": float(day_cost),
            "monthly_cost": float(month_cost),
            "daily_limit": settings.BUDGET_DAILY_LIMIT_USD,
            "monthly_limit": settings.BUDGET_MONTHLY_LIMIT_USD,
            "alert_threshold": settings.BUDGET_ALERT_THRESHOLD,
            # 缓存节省统计
            "daily_cache_savings_usd": float(day_savings),
            "monthly_cache_savings_usd": float(month_savings),
            "daily_cache_hit_rate": cache_hit_rate,
            # 分模型明细
            "breakdown": {
                row.model_name: {
                    "cost": float(row.cost or 0),
                    "cache_savings_usd": float(row.savings or 0),
                    "cache_hit_tokens": int(row.cache_hit_tokens or 0),
                    "total_input_tokens": int(row.total_input_tokens or 0),
                    "cache_hit_rate": round(
                        (row.cache_hit_tokens or 0) / max(row.total_input_tokens or 1, 1), 4
                    ),
                }
                for row in model_rows
            },
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
            msg = (
                f"🚨 [FATAL] Daily Budget EXCEEDED! "
                f"Spent: ${metrics['daily_cost']:.2f} / Limit: ${metrics['daily_limit']:.2f}"
            )
            logger.error(msg)
            alerts.append(msg)
            is_exceeded = True
        elif day_ratio >= metrics["alert_threshold"]:
            msg = f"⚠️ [WARN] Daily Budget Warning! Reached {day_ratio * 100:.1f}% of limit."
            logger.warning(msg)
            alerts.append(msg)

        # 每月检查
        month_ratio = metrics["monthly_cost"] / max(metrics["monthly_limit"], 0.01)
        if month_ratio >= 1.0:
            msg = (
                f"🚨 [FATAL] Monthly Budget EXCEEDED! "
                f"Spent: ${metrics['monthly_cost']:.2f} / Limit: ${metrics['monthly_limit']:.2f}"
            )
            logger.error(msg)
            alerts.append(msg)
            is_exceeded = True

        # 缓存节省提示（正向信息）
        if metrics["daily_cache_savings_usd"] > 0:
            logger.info(
                "💰 [Cache] Today saved ${:.4f} via prefix cache (hit rate={:.1%})",
                metrics["daily_cache_savings_usd"],
                metrics["daily_cache_hit_rate"],
            )

        return {
            "status": "EXCEEDED" if is_exceeded else ("WARNING" if alerts else "OK"),
            "alerts": alerts,
            "metrics": metrics,
        }


# 单例模式导出
budget_service = BudgetService()
