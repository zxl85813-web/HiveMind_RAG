"""
操作审计日志 — 记录 who/what/when/where。

所有关键操作通过 audit_log() 记录:
    - 用户操作 (创建知识库/删除对话)
    - 系统操作 (Agent 执行/LLM 调用)
    - 安全事件 (登录失败/权限拒绝)

参见: REGISTRY.md > 后端 > audit > logger
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from loguru import logger as app_logger


class AuditAction(str, Enum):
    """可审计的操作类型。"""

    # Auth
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"

    # Chat
    CHAT_SEND = "chat.send"
    CHAT_DELETE = "chat.delete"
    CONVERSATION_CREATE = "conversation.create"
    CONVERSATION_DELETE = "conversation.delete"

    # Knowledge
    KB_CREATE = "kb.create"
    KB_DELETE = "kb.delete"
    DOC_UPLOAD = "kb.doc.upload"
    DOC_DELETE = "kb.doc.delete"

    # Agent
    AGENT_INVOKE = "agent.invoke"
    AGENT_CONFIG_CHANGE = "agent.config.change"

    # Admin
    USER_CREATE = "admin.user.create"
    USER_UPDATE = "admin.user.update"
    USER_DELETE = "admin.user.delete"
    ROLE_CHANGE = "admin.role.change"
    SYSTEM_CONFIG = "admin.system.config"

    # Security
    PERMISSION_DENIED = "security.permission.denied"
    RATE_LIMITED = "security.rate.limited"


def audit_log(
    action: AuditAction,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """
    记录审计日志。

    Args:
        action: 操作类型
        user_id: 操作者 ID
        resource_type: 操作的资源类型 (kb, conversation, user 等)
        resource_id: 资源 ID
        details: 附加信息
        ip_address: 来源 IP

    示例:
        audit_log(
            AuditAction.KB_CREATE,
            user_id="user-123",
            resource_type="knowledge_base",
            resource_id="kb-456",
            details={"name": "技术文档"}
        )
    """
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action.value,
        "user_id": user_id or "system",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "ip": ip_address,
        "details": details or {},
    }

    # 结构化日志 — loguru 会自动序列化
    app_logger.bind(audit=True, entry=entry).info(
        "AUDIT | {action} | user={user} | {rtype}/{rid}",
        action=action.value,
        user=user_id or "system",
        rtype=resource_type or "-",
        rid=resource_id or "-",
    )

    # TODO: 持久化到 audit_logs 表
    # async with get_db_session() as db:
    #     db.add(AuditLog(**entry))
    #     await db.commit()
