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
import bcrypt

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.logging import logger

# === Password Hashing ===

def hash_password(password: str) -> str:
    """哈希密码。"""
    salt = bcrypt.gensalt()
    # bcrypt expectations: password as bytes
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码。"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


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


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建 JWT Refresh Token (较长有效期).
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "refresh"})
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
        raise AuthenticationError("Token has expired") from None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e} (Using SECRET_KEY starting with: {settings.SECRET_KEY[:4]}...)")
        raise AuthenticationError(f"Invalid token: {str(e)}") from e
