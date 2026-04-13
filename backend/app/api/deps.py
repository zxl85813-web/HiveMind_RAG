
"""
API 依赖注入系统

该模块定义了所有 FastAPI 路由通用的依赖项，涵盖了：
1. 数据库会话管理 (PostgreSQL / SQLAlchemy)
2. 身份认证与安全 (JWT /Bearer Token)
3. 角色权限控制 (RBAC)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.auth.security import decode_access_token
from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError
from app.models.chat import User

# 别名定义：保持与旧代码逻辑的向后兼容，用于快速获取数据库 Session
get_db = get_db_session

# 定义持票人令牌认证方案 (Bearer Token)
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    核心依赖：获取当前认证用户。
    
    该函数执行以下流程：
    1. 提取请求头中的 Authorization Bearer Token。
    2. 解码 JWT 并验证有效性及过期时间。
    3. 从数据库中加载用户模型。
    4. 检查用户是否处于激活（Active）状态。
    
    异常处理：
    - 若无 Token、Token 损坏或过期，抛出 401 Unauthorized。
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=" 未发现认证信息，请提供 Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # 解码令牌
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            logger.error(" 令牌载荷异常：缺少 sub 字段 (user_id)")
            raise AuthenticationError(" 无效的令牌载荷 ")

        # 从 DB 获取完整用户对象
        user = await db.get(User, user_id)
        if not user:
            logger.error(f" 未找到用户 ID: {user_id}")
            raise AuthenticationError(" 用户不存在 ")

        # 检查账号状态
        if not user.is_active:
            logger.error(f" 用户账号已停用: {user.username}")
            raise AuthenticationError(" 账号已处于停用状态 ")

        return user
    except AuthenticationError as e:
        logger.warning(f" 认证链路失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
    """
    可选依赖：尝试获取当前认证用户。
    
    主要用于公开预览页面或需要“千人千面”但非强制登录的场景。
    如果验证失败或无 Token，返回 None 而不是抛出异常。
    """
    if not credentials:
        return None
    try:
        user = await get_current_user(credentials, db)
        return user
    except HTTPException:
        # 捕获 401 并静默降级为访客身份
        return None


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    权限依赖：强制要求管理员身份。
    
    用于保护治理中心、安全配置、审计日志等高敏感接口。
    
    规约参考：
    - 🛰️ [RBAC-GOV]: 实现不区分大小写的角色匹配策略 (DEC-260413-003)。
    """
    # 🛡️ [RBAC-Harden]: 统一归一化角色进行比对 (兼容单数 role 字段)
    user_role = current_user.role.lower() if hasattr(current_user, 'role') else ""
    if user_role != "admin":
        logger.warning(f" 越权访问拦截: 用户 {current_user.name} 尝试访问管理员专属接口 ")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=" 权限不足：该操作仅限管理员 (Admin) 执行 ",
        )
    return current_user
