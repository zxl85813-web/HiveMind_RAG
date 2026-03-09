"""
Pydantic schemas for Security & Desensitization.
"""

from datetime import datetime

from pydantic import BaseModel


class DesensitizationPolicyBase(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True
    rules_json: str = "{}"


class DesensitizationPolicyCreate(DesensitizationPolicyBase):
    pass


class DesensitizationPolicyRead(DesensitizationPolicyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SensitiveItemRead(BaseModel):
    id: int
    report_id: str
    detector_type: str
    original_text_preview: str
    redacted_text: str
    start_index: int
    end_index: int
    action_taken: str

    class Config:
        from_attributes = True


class DesensitizationReportRead(BaseModel):
    id: str
    document_id: str
    total_items_found: int
    total_items_redacted: int
    status: str
    created_at: datetime
    items: list[SensitiveItemRead] = []

    class Config:
        from_attributes = True


class DocumentPermissionBase(BaseModel):
    document_id: str
    user_id: str | None = None
    role_id: str | None = None
    department_id: str | None = None
    can_read: bool = True
    can_write: bool = False


class DocumentPermissionCreate(DocumentPermissionBase):
    pass


class DocumentPermissionRead(DocumentPermissionBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogRead(BaseModel):
    id: str
    user_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details: str = "{}"
    ip_address: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True
