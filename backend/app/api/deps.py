from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.chat import User

# Alias for backwards compatibility with routes that import get_db
get_db = get_db_session

async def get_current_user() -> User:
    """
    Mock dependency for current user until full Auth is implemented.
    Returns a unified mock user so all endpoints (like memory, knowledge) 
    work smoothly without security token overhead during local dev.
    """
    return User(
        id="mock-user-001", 
        email="dev@hivemind.local", 
        hashed_password="mock",
        is_active=True,
        is_superuser=True
    )
