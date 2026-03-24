from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError
from app.models.chat import User

# Alias for backwards compatibility with routes that import get_db
get_db = get_db_session

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """获取当前认证用户（真实 JWT 验证）。"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")

        user = await db.get(User, user_id)
        if not user:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("Inactive user")

        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
    """获取当前认证用户（可选，验证失败不抛出 401）。"""
    if not credentials:
        return None
    try:
        user = await get_current_user(credentials, db)
        return user
    except HTTPException:
        return None
