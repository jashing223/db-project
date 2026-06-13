"""Map MySQL / application errors to HTTP exceptions."""

from __future__ import annotations

import pymysql
from fastapi import HTTPException


def raise_http_from_db_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc

    if isinstance(exc, pymysql.MySQLError):
        code = exc.args[0] if exc.args else 0
        message = str(exc.args[1]) if len(exc.args) > 1 else str(exc)

        if code == 1644:  # SIGNAL from triggers
            raise HTTPException(status_code=400, detail=message) from exc
        if code in (1062, 1586):  # duplicate entry
            raise HTTPException(status_code=409, detail=message) from exc
        raise HTTPException(status_code=500, detail=message) from exc

    raise HTTPException(status_code=500, detail=str(exc)) from exc


def not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{entity} not found")


def conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail=message)
