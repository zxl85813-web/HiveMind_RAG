"""
RBAC 权限管理 — 角色 + 权限 + 装饰器。

角色层级:
    - admin    → 所有权限
    - user     → 基础操作 (对话/查看知识库)
    - readonly → 只读

参见: REGISTRY.md > 后端 > auth > permissions
"""


from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.core.exceptions import ForbiddenError
from app.models.chat import User
from app.models.security import DocumentPermission
from app.schemas.auth import Permission, Role

# Definitions moved to app.schemas.auth


# 角色 → 权限映射
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: {p for p in Permission},  # 全部权限
    Role.USER: {
        Permission.CHAT_SEND,
        Permission.CHAT_VIEW,
        Permission.CHAT_DELETE,
        Permission.KB_CREATE,
        Permission.KB_VIEW,
        Permission.KB_UPLOAD,
        Permission.AGENT_VIEW,
    },
    Role.READONLY: {
        Permission.CHAT_VIEW,
        Permission.KB_VIEW,
        Permission.AGENT_VIEW,
    },
}


def has_permission(role: Role, permission: Permission) -> bool:
    """检查角色是否拥有某权限。"""
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(permission: Permission):
    """
    FastAPI 依赖注入装饰器 — 检查当前用户是否有权限。

    用法:
        @router.post("/knowledge/", dependencies=[Depends(require_permission(Permission.KB_CREATE))])
        async def create_kb(...):
            ...
    """

    async def checker(current_user: User = Depends(get_current_user)):
        # Role defaults to string since DB maps it. Here we safely check.
        if not has_permission(current_user.role, permission):
            raise ForbiddenError(
                message=f"Missing permission: {permission.value}",
                deny_reason="rbac_denied",
            )

    return checker


async def has_document_permission(db: AsyncSession, user: User, doc_id: str, required_level: str = "read") -> bool:
    """
    Check if user has 'read' or 'write' access to a specific document.
    """
    if user.role == Role.ADMIN:
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
