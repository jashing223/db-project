"""Role-based access control dependencies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException

from dependencies import get_current_user
from schemas.auth import CurrentUser

# Role levels (see api_spec.md)
ROLE_RECEPTION = 1
ROLE_NURSE = 2
ROLE_VET = 3
ROLE_MANAGER = 4

ALL_ROLES = frozenset({ROLE_RECEPTION, ROLE_NURSE, ROLE_VET, ROLE_MANAGER})
READ_ALL = (ROLE_RECEPTION, ROLE_NURSE, ROLE_VET, ROLE_MANAGER)
RECEPTION_MANAGER = (ROLE_RECEPTION, ROLE_MANAGER)
MEDICAL_WRITE = (ROLE_NURSE, ROLE_VET, ROLE_MANAGER)
MANAGER_ONLY = (ROLE_MANAGER,)
RECORD_LOCK = (ROLE_NURSE, ROLE_VET)


def require_roles(*allowed_levels: int) -> Callable[..., CurrentUser]:
    allowed = frozenset(allowed_levels)

    def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.Role_Level not in allowed:
            raise HTTPException(status_code=403, detail="權限不足")
        return user

    return _check
