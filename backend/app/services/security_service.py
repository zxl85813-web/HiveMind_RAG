"""
Security Service — Handles Desensitization policies and reports CRUD operations.
"""

import json
from contextlib import suppress
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.audit.security.engine import DesensitizationEngine
from app.models.security import AuditLog, DesensitizationPolicy, DesensitizationReport, SensitiveItem


class SecurityService:
    """Service to interact with DB for Security / Desensitization / ACL operations."""

    @staticmethod
    async def log_audit(
        db: AsyncSession,
        user_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Record a security event to the audit trail."""
        safe_details = details or {}
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(safe_details),
        )
        db.add(log)
        await db.commit()
        logger.info(f"🛡️ Audit: User {user_id} performed {action} on {resource_type}:{resource_id}")

    @staticmethod
    async def get_active_policy(db: AsyncSession) -> DesensitizationPolicy | None:
        """Fetch the currently active desensitization policy."""
        statement = select(DesensitizationPolicy).where(DesensitizationPolicy.is_active)
        result = await db.execute(statement)
        return result.scalars().first()

    @staticmethod
    async def apply_desensitization(
        text: str, policy_id: str | None = None, db: AsyncSession | None = None, doc_id: str | None = None
    ) -> tuple[str, list[dict]]:
        """
        Generic entry point for desensitization.
        """
        if not text:
            return text, []

        rules = {}
        if db:
            policy = None
            if policy_id:
                policy = await db.get(DesensitizationPolicy, policy_id)
            else:
                policy = await SecurityService.get_active_policy(db)

            if policy and policy.rules_json:
                with suppress(Exception):
                    rules = json.loads(policy.rules_json)

        redacted_text, applied_records = DesensitizationEngine.process_text(text, rules)

        if applied_records and db and doc_id:
            await SecurityService.save_desensitization_report(db, doc_id, applied_records)

        return redacted_text, applied_records

    @staticmethod
    async def save_desensitization_report(db: AsyncSession, doc_id: str, applied_records: list[dict]):
        """Helper to save report items to DB."""
        report = DesensitizationReport(
            document_id=doc_id,
            total_items_found=len(applied_records),
            total_items_redacted=len(applied_records),
            status="completed",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        items_to_add = [
            SensitiveItem(
                report_id=report.id,
                detector_type=record["detector_type"],
                original_text_preview=record.get("original_text_preview", ""),
                redacted_text=record["redacted_text"],
                start_index=record["start_index"],
                end_index=record["end_index"],
                action_taken=record["action_taken"],
            )
            for record in applied_records
        ]
        db.add_all(items_to_add)
        await db.commit()
        logger.info(f"🛡️ Saved desensitization report for Doc {doc_id} ({len(applied_records)} items)")
