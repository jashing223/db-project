"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated, Generator

import pymysql
from fastapi import Header, HTTPException

from auth import decode_access_token
from db import get_connection
from schemas.auth import CurrentUser


def get_db() -> Generator[pymysql.connections.Connection, None, None]:
    with get_connection() as conn:
        yield conn


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登入或 token 無效")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="未登入或 token 無效")

    try:
        return decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="未登入或 token 無效") from None
