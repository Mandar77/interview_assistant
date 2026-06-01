"""
Auth FastAPI dependencies - current user resolution & role guards.
Location: backend/services/auth_service/dependencies.py
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import get_repository
from models.platform_schemas import PublicUser, UserRole
from services.auth_service.security import decode_access_token

# auto_error=False so endpoints can support optional/anonymous auth.
_bearer = HTTPBearer(auto_error=False)

USERS_COLLECTION = "users"


async def _user_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[PublicUser]:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    repo = get_repository()
    doc = await repo.get(USERS_COLLECTION, user_id)
    if not doc:
        return None
    return PublicUser(
        id=doc["id"],
        email=doc["email"],
        username=doc["username"],
        full_name=doc.get("full_name"),
        role=doc["role"],
        org_id=doc.get("org_id"),
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[PublicUser]:
    """Return the authenticated user if a valid token is present, else None."""
    return await _user_from_credentials(credentials)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> PublicUser:
    """Require a valid token; 401 otherwise."""
    user = await _user_from_credentials(credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*roles: UserRole):
    """Dependency factory enforcing that the user holds one of ``roles``."""

    async def _guard(user: PublicUser = Depends(get_current_user)) -> PublicUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return user

    return _guard


async def get_employer_user(
    user: PublicUser = Depends(get_current_user),
) -> PublicUser:
    """Require an employer (admin or member) with an org."""
    if user.role not in (UserRole.EMPLOYER_ADMIN, UserRole.EMPLOYER_MEMBER):
        raise HTTPException(status_code=403, detail="Employer account required")
    if not user.org_id:
        raise HTTPException(status_code=403, detail="No organization associated")
    return user
