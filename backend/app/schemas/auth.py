from enum import StrEnum

from pydantic import BaseModel


class Role(StrEnum):
    """用户角色。"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

class Permission(StrEnum):
    """细粒度权限。"""
    # Chat
    CHAT_SEND = "chat:send"
    CHAT_VIEW = "chat:view"
    CHAT_DELETE = "chat:delete"
    # Knowledge
    KB_CREATE = "kb:create"
    KB_VIEW = "kb:view"
    KB_DELETE = "kb:delete"
    KB_UPLOAD = "kb:upload"
    # Agent
    AGENT_VIEW = "agent:view"
    AGENT_CONFIG = "agent:config"
    # Admin
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"
    AUDIT_VIEW = "audit:view"

class AuthorizationContext(BaseModel):
    """
    统一授权结果上下文 (ARM-P0-4)。
    供后续 Prompt 层消费，确保记忆增强不越权。
    """
    user_id: str
    role: str
    department_id: str | None = None
    # 授权作用域
    authorized_kb_ids: list[str] = []
    authorized_doc_ids: list[str] = []
    # 动作权限快照 (可选)
    permissions: list[str] = []
