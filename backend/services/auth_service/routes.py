"""
Auth Service API Routes - signup, login, current user (Phase 9).
Location: backend/services/auth_service/routes.py
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException

from db import get_repository
from models.platform_schemas import (
    LoginRequest,
    Organization,
    PublicUser,
    SignupRequest,
    TokenResponse,
    User,
    UserRole,
)
from services.auth_service.dependencies import get_current_user
from services.auth_service.security import (
    create_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter()

USERS = "users"
ORGS = "organizations"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def _public(user_doc: dict) -> PublicUser:
    return PublicUser(
        id=user_doc["id"],
        email=user_doc["email"],
        username=user_doc["username"],
        full_name=user_doc.get("full_name"),
        role=user_doc["role"],
        org_id=user_doc.get("org_id"),
    )


@router.post("/signup", response_model=TokenResponse)
async def signup(req: SignupRequest):
    """Register a candidate or employer admin. Employer admins create an org."""
    repo = get_repository()

    # Uniqueness checks (email + username).
    if await repo.find(USERS, where={"email": req.email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    if await repo.find(USERS, where={"username": req.username}):
        raise HTTPException(status_code=409, detail="Username already taken")

    org_id = None
    if req.role == UserRole.EMPLOYER_ADMIN:
        if not req.organization_name:
            raise HTTPException(
                status_code=400,
                detail="organization_name is required for employer signup",
            )
        org = Organization(
            name=req.organization_name,
            slug=_slugify(req.organization_name),
        )
        await repo.insert(ORGS, org.model_dump())
        org_id = org.id

    user = User(
        email=req.email,
        username=req.username,
        full_name=req.full_name,
        role=req.role,
        org_id=org_id,
        password_hash=hash_password(req.password),
    )
    doc = await repo.insert(USERS, user.model_dump())

    if org_id:
        await repo.update(ORGS, org_id, {"created_by": user.id})

    token = create_access_token(user.id, user.role.value, org_id)
    return TokenResponse(access_token=token, user=_public(doc))


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate by email or username + password."""
    repo = get_repository()

    matches = await repo.find(USERS, where={"email": req.email_or_username})
    if not matches:
        matches = await repo.find(USERS, where={"username": req.email_or_username})
    if not matches:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_doc = matches[0]
    if not verify_password(req.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        user_doc["id"], user_doc["role"], user_doc.get("org_id")
    )
    return TokenResponse(access_token=token, user=_public(user_doc))


@router.get("/me", response_model=PublicUser)
async def me(user: PublicUser = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return user


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "auth"}
