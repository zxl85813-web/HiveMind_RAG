"""
RBAC 权限模块单元测试。

覆盖:
    - 角色-权限映射
    - has_permission 检查
    - has_document_permission 文档级 ACL
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.auth.permissions import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    has_permission,
    has_document_permission,
)


class TestRolePermissionMapping:
    """角色-权限映射表验证。"""

    def test_admin_has_all_permissions(self):
        for perm in Permission:
            assert has_permission(Role.ADMIN, perm), f"Admin missing {perm}"

    def test_user_can_chat(self):
        assert has_permission(Role.USER, Permission.CHAT_SEND)
        assert has_permission(Role.USER, Permission.CHAT_VIEW)

    def test_user_can_manage_kb(self):
        assert has_permission(Role.USER, Permission.KB_CREATE)
        assert has_permission(Role.USER, Permission.KB_VIEW)
        assert has_permission(Role.USER, Permission.KB_UPLOAD)

    def test_user_cannot_manage_users(self):
        assert not has_permission(Role.USER, Permission.USER_MANAGE)
        assert not has_permission(Role.USER, Permission.SYSTEM_CONFIG)

    def test_readonly_can_only_view(self):
        assert has_permission(Role.READONLY, Permission.CHAT_VIEW)
        assert has_permission(Role.READONLY, Permission.KB_VIEW)
        assert has_permission(Role.READONLY, Permission.AGENT_VIEW)

    def test_readonly_cannot_write(self):
        assert not has_permission(Role.READONLY, Permission.CHAT_SEND)
        assert not has_permission(Role.READONLY, Permission.KB_CREATE)
        assert not has_permission(Role.READONLY, Permission.KB_UPLOAD)
        assert not has_permission(Role.READONLY, Permission.KB_DELETE)

    def test_unknown_role_has_no_permissions(self):
        assert not has_permission("unknown_role", Permission.CHAT_VIEW)
