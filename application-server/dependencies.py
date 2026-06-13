"""FastAPI dependencies."""

from __future__ import annotations

from typing import Generator

import pymysql

from db import get_connection


def get_db() -> Generator[pymysql.connections.Connection, None, None]:
    with get_connection() as conn:
        yield conn
