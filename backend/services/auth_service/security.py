"""
Auth security primitives - password hashing + JWT issue/verify.
Location: backend/services/auth_service/security.py
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt

from config.settings import settings

logger = logging.getLogger(__name__)


def _to_bytes(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes; truncate explicitly to avoid the
    # ValueError raised by bcrypt 5.x on longer inputs.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(password), password_hash.encode("utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning("Password verify failed: %s", e)
        return False


def create_access_token(
    subject: str,
    role: str,
    org_id: Optional[str] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """Issue a signed JWT for ``subject`` (user id)."""
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.jwt_expire_minutes
    )
    payload = {
        "sub": subject,
        "role": role,
        "org_id": org_id,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """Return the JWT payload, or None if invalid/expired."""
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as e:
        logger.debug("JWT decode failed: %s", e)
        return None
