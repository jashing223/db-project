"""MySQL connection helper — loads settings from application-server/.env."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pymysql
import pymysql.cursors

APP_DIR = Path(__file__).resolve().parent
ENV_PATH = APP_DIR / ".env"


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


@contextmanager
def get_connection() -> Generator[pymysql.connections.Connection, None, None]:
    """Yield a PyMySQL connection with DictCursor; commit on success, rollback on error."""
    settings = _db_settings()
    conn = pymysql.connect(
        host=settings["host"],
        port=settings["port"],
        user=settings["user"],
        password=settings["password"],
        database=settings["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
