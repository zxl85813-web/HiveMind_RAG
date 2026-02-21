"""
认证与安全模块。

提供:
    - JWT Token 生成与验证
    - 密码哈希
    - FastAPI 依赖注入: get_current_user

参见: REGISTRY.md > 后端 > 核心配置 > security
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.logging import logger

# === Password Hashing ===
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """哈希密码。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码。"""
    return pwd_context.verify(plain_password, hashed_password)


# === JWT Token ===

ALGORITHM = "HS256"


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建 JWT Access Token.

    Args:
        data: Token payload (至少包含 "sub" 字段)
        expires_delta: 过期时长，默认使用 settings 配置
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    解码并验证 JWT Token。

    Raises:
        AuthenticationError: Token 无效或过期
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: {}", e)
        raise AuthenticationError("Invalid token")


# === FastAPI 依赖注入 ===
# TODO: 完成以下依赖函数，集成到路由中

# from fastapi import Depends
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
#
# security_scheme = HTTPBearer(auto_error=False)
#
# async def get_current_user(
#     credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
#     db: AsyncSession = Depends(get_db_session),
# ) -> User:
#     """获取当前认证用户。"""
#     if not credentials:
#         raise AuthenticationError()
#     payload = decode_access_token(credentials.credentials)
#     user_id = payload.get("sub")
#     user = await db.get(User, user_id)
#     if not user:
#         raise AuthenticationError("User not found")
#     return user
