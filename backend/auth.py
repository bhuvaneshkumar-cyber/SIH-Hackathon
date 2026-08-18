"""
auth.py — JWT-based doctor authentication for ClinDoc AI demo.

Demo credentials (hardcoded — not for production use):
    email:    doctor@clindoc.ai
    password: demo2026

Design:
    - POST /auth/login  → returns {access_token, token_type}
    - All clinical endpoints require  Authorization: Bearer <token>
    - Token lifetime: 8 hours (enough for a full demo day)
    - Algorithm: HS256 with a local secret key

Dependencies: python-jose
(Passlib/bcrypt avoided due to passlib 1.7.4 + bcrypt 5.x incompatibility
on Python 3.14. Using stdlib hashlib PBKDF2-HMAC-SHA256 instead.)
"""

from __future__ import annotations

import os
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# In production, pull this from an environment variable / vault.
_SECRET_KEY = os.getenv(
    "CLINDOC_JWT_SECRET",
    "SIH2026-clindoc-demo-secret-do-not-use-in-production",
)
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 8

# ---------------------------------------------------------------------------
# Password hashing (stdlib PBKDF2 — no external C deps)
# ---------------------------------------------------------------------------
_SALT = b"clindoc-sih2026-demo-salt"  # fixed salt is fine for a demo


def _hash_password(password: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), _SALT, 260_000)
    return dk.hex()


# Pre-computed hash of "demo2026" with the salt above
_DEMO_HASH = _hash_password("demo2026")

# ---------------------------------------------------------------------------
# Demo user store (in-memory; no DB required)
# ---------------------------------------------------------------------------
_USERS: dict[str, dict] = {
    "doctor@clindoc.ai": {
        "email": "doctor@clindoc.ai",
        "full_name": "Dr. Priya Nair",
        "role": "physician",
        "hashed_password": _DEMO_HASH,
        "disabled": False,
    },
}

# ---------------------------------------------------------------------------
# OAuth2 scheme — token URL path must match the login route
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(_hash_password(plain), hashed)


def _create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(hours=_TOKEN_EXPIRE_HOURS)
    )
    payload["exp"] = expire
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def authenticate_user(email: str, password: str) -> dict | None:
    """Return user dict if credentials are valid, else None."""
    user = _USERS.get(email)
    if not user:
        return None
    if not _verify_password(password, user["hashed_password"]):
        return None
    return user


def create_login_token(user: dict) -> str:
    return _create_access_token(
        data={"sub": user["email"], "role": user["role"]},
        expires_delta=timedelta(hours=_TOKEN_EXPIRE_HOURS),
    )


# ---------------------------------------------------------------------------
# FastAPI dependency — inject into any protected route
# ---------------------------------------------------------------------------
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Decode and validate the JWT from the Authorization header.
    Raises 401 if invalid or expired.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        email: str | None = payload.get("sub")
        if not email:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = _USERS.get(email)
    if not user or user.get("disabled"):
        raise credentials_exc
    return user
