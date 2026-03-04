"""
Security Service — Handles Desensitization policies and reports CRUD operations.
"""
from typing import List, Optional, Dict
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from loguru import logger

from app.models.security import DesensitizationPolicy, DesensitizationReport, SensitiveItem, AuditLog, DocumentPermission
from app.models.chat import User
from app.services.security.engine import DesensitizationEngine


class SecurityService:
    """Service to interact with DB for Security / Desensitization / ACL operations."""

    @staticmethod
    async def log_audit(
        db: AsyncSession, 
        user_id: Optional[str], 
        action: str, 
        resource_type: str, 
        resource_id: Optional[str] = None,
        details: dict = {}
    ):
        """Record a security event to the audit trail."""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details)
        )
        db.add(log)
        await db.commit()
        logger.info(f"🛡️ Audit: User {user_id} performed {action} on {resource_type}:{resource_id}")

    @staticmethod
    async def has_permission(
        db: AsyncSession, 
        user: User, 
        doc_id: str, 
        required_level: str = "read"
    ) -> bool:
        """
        Check if user has 'read' or 'write' access to a specific document.
        """
        if user.role == "admin":
            return True

        statement = select(DocumentPermission).where(DocumentPermission.document_id == doc_id)
        result = await db.execute(statement)
        perms = result.scalars().all()

        for p in perms:
            if p.user_id == user.id:
                return p.can_write if required_level == "write" else p.can_read
            if p.role_id == user.role:
                return p.can_write if required_level == "write" else p.can_read
            if p.department_id == user.department_id and user.department_id is not None:
                return p.can_write if required_level == "write" else p.can_read

        return False

    @staticmethod
    async def get_active_policy(db: AsyncSession) -> Optional[DesensitizationPolicy]:
        """Fetch the currently active desensitization policy."""
        statement = select(DesensitizationPolicy).where(DesensitizationPolicy.is_active == True)
        result = await db.execute(statement)
        return result.scalars().first()

    @staticmethod
    async def apply_desensitization(
        text: str,
        policy_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        doc_id: Optional[str] = None
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
                try:
                    rules = json.loads(policy.rules_json)
                except Exception:
                    pass
        
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
            status="completed"
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
                action_taken=record["action_taken"]
            )
            for record in applied_records
        ]
        db.add_all(items_to_add)
        await db.commit()
        logger.info(f"🛡️ Saved desensitization report for Doc {doc_id} ({len(applied_records)} items)")
