"""Shared FastAPI dependencies.

Auth dependencies are stubs for Phase 0 — will be implemented with JWT
in Phase 2.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Stub — will decode JWT and fetch user in Phase 2."""
    if credentials is None:
        return None
    # TODO Phase 2: decode JWT, query users table
    return None


async def require_user(user: User | None = Depends(get_current_user)) -> User:
    """Require an authenticated user (contributor or admin)."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def require_admin(user: User = Depends(require_user)) -> User:
    """Require an admin user."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user
