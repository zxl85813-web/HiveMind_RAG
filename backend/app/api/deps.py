from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.tenant_context import set_current_tenant
from app.models.chat import User
from app.models.tenant import DEFAULT_TENANT_ID
from app.auth.security import decode_access_token
from app.core.exceptions import AuthenticationError

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

        # Bind tenant for the rest of this request — singletons / services
        # downstream read it via app.core.tenant_context.get_current_tenant().
        # Pre-multi-tenant rows fall back to DEFAULT_TENANT_ID.
        tenant_id = getattr(user, "tenant_id", None) or DEFAULT_TENANT_ID
        set_current_tenant(tenant_id)

        # Pre-warm per-tenant LLM-key cache so LLMRouter (sync hot path) can
        # see overrides without touching the DB. Best-effort — failures must
        # never block authentication.
        if tenant_id != DEFAULT_TENANT_ID:
            try:
                from app.services.governance.secret_manager import ensure_loaded
                from app.agents.llm_router import all_provider_secret_keys
                await ensure_loaded(db, tenant_id, all_provider_secret_keys())
            except Exception as exc:  # noqa: BLE001
                # Module may not be importable in minimal test envs.
                pass

        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Reject non-admin callers (HTTP 403)."""
    if getattr(user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def assert_tenant_owns(resource, user: User, *, kind: str = "resource") -> None:
    """Raise 404 if `resource` does not belong to `user.tenant_id`.

    Returns 404 (not 403) so attackers can't probe for existence of
    cross-tenant IDs. Admins of the same tenant still pass.
    """
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{kind} not found")
    user_tenant = getattr(user, "tenant_id", None) or DEFAULT_TENANT_ID
    res_tenant = getattr(resource, "tenant_id", None) or DEFAULT_TENANT_ID
    if user_tenant != res_tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{kind} not found")
