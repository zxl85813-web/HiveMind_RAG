"""
RBAC 权限管理 — 角色 + 权限 + 装饰器。

角色层级:
    - admin    → 所有权限
    - user     → 基础操作 (对话/查看知识库)
    - readonly → 只读

参见: REGISTRY.md > 后端 > auth > permissions
"""

from enum import Enum


class Role(str, Enum):
    """用户角色。"""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class Permission(str, Enum):
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


# 角色 → 权限映射
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),  # 全部权限
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
    # TODO: 实现 — 需配合 get_current_user 使用
    # async def checker(current_user: User = Depends(get_current_user)):
    #     if not has_permission(current_user.role, permission):
    #         raise ForbiddenError(f"Missing permission: {permission}")
    # return checker
    pass
