"""
Security API endpoints.
"""
from typing import List, Dict, Any
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from app.api.deps import get_db, get_current_user
from app.common.response import ApiResponse
from app.models.security import DesensitizationPolicy, DesensitizationReport, SensitiveItem
from app.schemas.security import DesensitizationPolicyRead, DesensitizationPolicyCreate, DesensitizationReportRead
from app.models.chat import User

router = APIRouter()


@router.get("/policies", response_model=ApiResponse[List[DesensitizationPolicyRead]])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all desensitization policies."""
    statement = select(DesensitizationPolicy).order_by(DesensitizationPolicy.id.desc())
    result = await db.execute(statement)
    policies = result.scalars().all()
    return ApiResponse.ok(data=policies)


@router.post("/policies", response_model=ApiResponse[DesensitizationPolicyRead])
async def create_policy(
    policy_in: DesensitizationPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new policy."""
    
    # If this one is active, deactivate others
    if policy_in.is_active:
        stmt = update(DesensitizationPolicy).values(is_active=False)
        await db.execute(stmt)

    db_obj = DesensitizationPolicy.model_validate(policy_in)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return ApiResponse.ok(data=db_obj)


@router.put("/policies/{policy_id}/activate", response_model=ApiResponse)
async def activate_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a specific policy and deactivate others."""
    stmt = update(DesensitizationPolicy).values(is_active=False)
    await db.execute(stmt)
    
    policy = await db.get(DesensitizationPolicy, policy_id)
    if not policy:
        return ApiResponse.error(message="Policy not found", code=404)
        
    policy.is_active = True
    db.add(policy)
    await db.commit()
    
    return ApiResponse.ok(message="Policy activated successfully")


@router.get("/reports/document/{document_id}", response_model=ApiResponse[DesensitizationReportRead])
async def get_report_for_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the redaction report for a specific document."""
    # Use join query if needed or lazy load
    statement = select(DesensitizationReport).where(DesensitizationReport.document_id == document_id)
    result = await db.execute(statement)
    report = result.scalars().first()
    
    if not report:
        return ApiResponse.error(message="Report not found", code=404)
        
    # Load items
    items_stmt = select(SensitiveItem).where(SensitiveItem.report_id == report.id)
    items_result = await db.execute(items_stmt)
    items = items_result.scalars().all()
    
    report_dict = report.model_dump()
    report_dict["items"] = items
    
    return ApiResponse.ok(data=report_dict)

@router.get("/detectors", response_model=ApiResponse[Dict[str, Any]])
async def get_available_detectors(current_user: User = Depends(get_current_user)):
    """List all registered detectors with their descriptions."""
    from app.audit.security.detectors import DetectorRegistry
    detectors = DetectorRegistry.get_all()
    
    res = []
    for d_type, d_obj in detectors.items():
        res.append({
            "type": d_type,
            "description": d_obj.__doc__ or f"Built-in {d_type} detector",
            "regex": getattr(d_obj, 'pattern', None).pattern if hasattr(d_obj, 'pattern') else "Custom Logic"
        })
        
    return ApiResponse.ok(data={"available_detectors": res})


# --- ACL & Governance (P1) ---

from app.models.security import DocumentPermission, AuditLog
from app.schemas.security import DocumentPermissionCreate, DocumentPermissionRead, AuditLogRead
from app.services.security_service import SecurityService

@router.get("/permissions/document/{document_id}", response_model=ApiResponse[List[DocumentPermissionRead]])
async def get_document_permissions(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all explicit permissions for a document."""
    stmt = select(DocumentPermission).where(DocumentPermission.document_id == document_id)
    res = await db.execute(stmt)
    return ApiResponse.ok(data=res.scalars().all())

@router.post("/permissions", response_model=ApiResponse[DocumentPermissionRead])
async def grant_permission(
    perm_in: DocumentPermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Grant or update a permission for a user/role/dept on a document."""
    # Audit trail
    await SecurityService.log_audit(
        db, current_user.id, "grant_permission", "document", 
        perm_in.document_id, details=perm_in.model_dump()
    )
    
    db_obj = DocumentPermission.model_validate(perm_in)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return ApiResponse.ok(data=db_obj)

@router.delete("/permissions/{permission_id}")
async def revoke_permission(
    permission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a specific permission."""
    perm = await db.get(DocumentPermission, permission_id)
    if not perm:
        return ApiResponse.error(message="Permission not found", code=404)
    
    # Audit trail
    await SecurityService.log_audit(
        db, current_user.id, "revoke_permission", "document", 
        perm.document_id, details={"perm_id": permission_id}
    )
    
    await db.delete(perm)
    await db.commit()
    return ApiResponse.ok(message="Permission revoked")

@router.get("/audit/logs", response_model=ApiResponse[List[AuditLogRead]])
async def list_audit_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View system audit logs (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    res = await db.execute(stmt)
    return ApiResponse.ok(data=res.scalars().all())
