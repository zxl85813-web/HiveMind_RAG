"""
Authentication & User Profile Endpoints.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.auth.security import create_access_token, verify_password
from app.common.response import ApiResponse
from app.core.config import settings
from app.core.logging import logger
from app.models.chat import User

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login endpoint to get a JWT token.
    In dev mode, if username is 'developer', it uses the mock user.
    """
    statement = select(User).where(User.username == payload.username)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user:
        logger.warning(f"Login failed: User '{payload.username}' not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    logger.debug(f"Attempting login for user: {user.username}")
    if not verify_password(payload.password, user.hashed_password):
        logger.warning(f"Login failed: Incorrect password for user '{payload.username}'")
        # 🛠️ [Dev-Hardening]: 移除硬编码调试，使用 Profile 里的调试开关 (REQ-SEC-004)
        if not (settings.DEBUG and user.username == "developer"):
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

    access_token = create_access_token(data={"sub": user.id})
    
    return ApiResponse.ok(data={
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    })


@router.get("/me", response_model=ApiResponse[dict[str, Any]])
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user information.
    """
    return ApiResponse.ok(data={
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "permissions": [], # TODO: Fetch real permissions if needed
    })
