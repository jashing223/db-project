"""Demo JWT authentication — Staff_ID login, no password."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt

from db import load_env
from schemas.auth import CurrentUser

_ALGORITHM = "HS256"
_DEFAULT_TTL_HOURS = 8
_DEFAULT_SECRET = "demo-pet-hospital-secret-change-in-production"


def _auth_secret() -> str:
    env = load_env()
    return (
        env.get("AUTH_SECRET")
        or os.environ.get("AUTH_SECRET")
        or _DEFAULT_SECRET
    )


def _token_ttl_hours() -> int:
    env = load_env()
    raw = env.get("AUTH_TOKEN_TTL_HOURS") or os.environ.get("AUTH_TOKEN_TTL_HOURS")
    if raw is None:
        return _DEFAULT_TTL_HOURS
    return int(raw)


def create_access_token(user: CurrentUser) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.Staff_ID),
        "Staff_ID": user.Staff_ID,
        "Staff_Name": user.Staff_Name,
        "Role_Level": user.Role_Level,
        "Specialty": user.Specialty,
        "iat": now,
        "exp": now + timedelta(hours=_token_ttl_hours()),
    }
    return jwt.encode(payload, _auth_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> CurrentUser:
    payload = jwt.decode(token, _auth_secret(), algorithms=[_ALGORITHM])
    return CurrentUser(
        Staff_ID=int(payload["Staff_ID"]),
        Staff_Name=str(payload["Staff_Name"]),
        Role_Level=int(payload["Role_Level"]),
        Specialty=payload.get("Specialty"),
    )
