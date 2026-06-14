"""MySQL connection helper — loads settings from application-server/.env."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pymysql
import pymysql.cursors
from dbutils.pooled_db import PooledDB

APP_DIR = Path(__file__).resolve().parent
ENV_PATH = APP_DIR / ".env"

_pool: PooledDB | None = None


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def _db_settings() -> dict:
    env = load_env()
    return {
        "host": env.get("DB_HOST") or os.environ["DB_HOST"],
        "port": int(env.get("DB_PORT") or os.environ.get("DB_PORT", "3306")),
        "user": env.get("DB_USER") or os.environ["DB_USER"],
        "password": env.get("DB_PASSWORD") or os.environ["DB_PASSWORD"],
        "database": env.get("DB_NAME") or os.environ["DB_NAME"],
    }


def _pool_settings() -> dict[str, int]:
    env = load_env()
    return {
        "maxconnections": int(env.get("DB_POOL_MAX") or os.environ.get("DB_POOL_MAX", "10")),
        "mincached": int(env.get("DB_POOL_MIN") or os.environ.get("DB_POOL_MIN", "1")),
        "maxcached": int(env.get("DB_POOL_MAX_IDLE") or os.environ.get("DB_POOL_MAX_IDLE", "5")),
    }


def init_pool() -> PooledDB:
    """Create the connection pool if it does not exist yet."""
    global _pool
    if _pool is not None:
        return _pool

    settings = _db_settings()
    pool_settings = _pool_settings()
    _pool = PooledDB(
        creator=pymysql,
        maxconnections=pool_settings["maxconnections"],
        mincached=pool_settings["mincached"],
        maxcached=pool_settings["maxcached"],
        maxshared=0,
        blocking=True,
        ping=1,
        host=settings["host"],
        port=settings["port"],
        user=settings["user"],
        password=settings["password"],
        database=settings["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    return _pool


def close_pool() -> None:
    """Drain and close the connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_connection() -> Generator[pymysql.connections.Connection, None, None]:
    """Yield a pooled PyMySQL connection; commit on success, rollback on error."""
    pool = init_pool()
    conn = pool.connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
