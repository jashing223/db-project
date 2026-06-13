#!/usr/bin/env python3
"""CLI: staged checks for MySQL connectivity and schema readiness."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pymysql.connections

from db import ENV_PATH, get_connection, load_env

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
DDL_DIR = REPO_ROOT / "database"
DDL_FILES = ("tables.DDL", "views.DDL", "triggers.DDL")

EXPECTED_TABLES = (
    "Owners",
    "PetBase",
    "Staff",
    "Doctors",
    "Catalog_Items",
    "Appointments",
    "Medical_Records",
    "Treatment_Details",
    "Invoices",
)

EXPECTED_VIEWS = ("Pets",)

StageStatus = Literal["pass", "fail", "skip"]
STAGE_COUNT = 4


@dataclass
class StageResult:
    number: int
    name: str
    status: StageStatus
    lines: list[str]


def _missing_config() -> list[str]:
    env = load_env(ENV_PATH)
    missing: list[str] = []
    for key in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        if not (env.get(key) or os.environ.get(key)):
            missing.append(key)
    return missing


def _connection_target() -> str:
    env = load_env(ENV_PATH)
    host = env.get("DB_HOST") or os.environ.get("DB_HOST", "?")
    port = env.get("DB_PORT") or os.environ.get("DB_PORT", "3306")
    database = env.get("DB_NAME") or os.environ.get("DB_NAME", "?")
    user = env.get("DB_USER") or os.environ.get("DB_USER", "?")
    return f"{user}@{host}:{port}/{database}"


def _print_ddl_locations() -> None:
    print("\nSchema DDL files (load in order if schema is missing):")
    for name in DDL_FILES:
        path = DDL_DIR / name
        status = "found" if path.is_file() else "missing"
        print(f"  [{status}] {path}")


def _print_stage(result: StageResult) -> None:
    label = result.status.upper()
    print(f"[{result.number}/{STAGE_COUNT}] {result.name} ... {label}")
    for line in result.lines:
        print(f"      {line}")


def _skip_stage(number: int, name: str, reason: str) -> StageResult:
    return StageResult(number, name, "skip", [reason])


def check_configuration() -> StageResult:
    missing = _missing_config()
    if missing:
        return StageResult(
            1,
            "Configuration",
            "fail",
            [
                f"Missing: {', '.join(missing)}",
                f"Copy {APP_DIR / '.env.example'} to {ENV_PATH} and fill in values.",
            ],
        )
    return StageResult(
        1,
        "Configuration",
        "pass",
        [f"Target: {_connection_target()}"],
    )


def check_connectability(conn: pymysql.connections.Connection) -> StageResult:
    target = _connection_target()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 AS ok")
        row = cur.fetchone()
        if not row or row.get("ok") != 1:
            return StageResult(
                2,
                "Connectability",
                "fail",
                ["Connection opened but sanity query returned unexpected result."],
            )

        cur.execute("SELECT VERSION() AS version")
        version_row = cur.fetchone() or {}
        version = version_row.get("version", "unknown")

    return StageResult(
        2,
        "Connectability",
        "pass",
        [f"Connected to {target}", f"MySQL version: {version}"],
    )


def check_tables(conn: pymysql.connections.Connection) -> StageResult:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_TYPE = 'BASE TABLE'
            """
        )
        existing = {row["TABLE_NAME"] for row in cur.fetchall()}

    missing_tables = [name for name in EXPECTED_TABLES if name not in existing]
    if missing_tables:
        lines = [f"Missing {len(missing_tables)} of {len(EXPECTED_TABLES)} core tables:"]
        lines.extend(f"- {name}" for name in missing_tables)
        lines.append(f"Load schema from {DDL_DIR / 'tables.DDL'}")
        return StageResult(3, "Core tables", "fail", lines)

    return StageResult(
        3,
        "Core tables",
        "pass",
        [f"All {len(EXPECTED_TABLES)} core tables present."],
    )


def check_views(conn: pymysql.connections.Connection) -> StageResult:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = DATABASE()
            """
        )
        existing = {row["TABLE_NAME"] for row in cur.fetchall()}

    missing_views = [name for name in EXPECTED_VIEWS if name not in existing]
    if missing_views:
        lines = [f"Missing {len(missing_views)} of {len(EXPECTED_VIEWS)} views:"]
        lines.extend(f"- {name}" for name in missing_views)
        lines.append(f"Load schema from {DDL_DIR / 'views.DDL'}")
        return StageResult(4, "Views", "fail", lines)

    return StageResult(
        4,
        "Views",
        "pass",
        [f"All {len(EXPECTED_VIEWS)} expected views present."],
    )


def db_readiness() -> tuple[bool, str]:
    """Return whether the database is configured, reachable, and schema-ready."""
    stage1 = check_configuration()
    if stage1.status != "pass":
        return False, stage1.lines[0] if stage1.lines else "Database configuration incomplete"

    try:
        with get_connection() as conn:
            for check_fn in (check_connectability, check_tables, check_views):
                result = check_fn(conn)
                if result.status != "pass":
                    reason = result.lines[0] if result.lines else f"{result.name} check failed"
                    return False, reason
    except Exception as exc:
        return False, str(exc)

    return True, "Database ready"


def is_db_ready() -> bool:
    ready, _ = db_readiness()
    return ready


def _print_remaining_skips(results: list[StageResult], start_number: int) -> None:
    remaining = [
        (2, "Connectability"),
        (3, "Core tables"),
        (4, "Views"),
    ]
    for number, name in remaining:
        if number >= start_number and not any(result.number == number for result in results):
            skipped = _skip_stage(number, name, "Skipped because a previous stage failed.")
            results.append(skipped)
            _print_stage(skipped)


def main() -> int:
    results: list[StageResult] = []

    stage1 = check_configuration()
    results.append(stage1)
    _print_stage(stage1)
    if stage1.status != "pass":
        _print_remaining_skips(results, 2)
        _print_ddl_locations()
        return 1

    try:
        with get_connection() as conn:
            stage2 = check_connectability(conn)
            results.append(stage2)
            _print_stage(stage2)
            if stage2.status != "pass":
                _print_remaining_skips(results, 3)
                _print_ddl_locations()
                return 1

            stage3 = check_tables(conn)
            results.append(stage3)
            _print_stage(stage3)
            if stage3.status != "pass":
                skipped = _skip_stage(4, "Views", "Skipped because core tables are missing.")
                results.append(skipped)
                _print_stage(skipped)
                _print_ddl_locations()
                return 1

            stage4 = check_views(conn)
            results.append(stage4)
            _print_stage(stage4)
            if stage4.status != "pass":
                _print_ddl_locations()
                return 1
    except Exception as exc:
        stage2 = StageResult(
            2,
            "Connectability",
            "fail",
            [f"Could not connect to {_connection_target()}", str(exc)],
        )
        results.append(stage2)
        _print_stage(stage2)
        _print_remaining_skips(results, 3)
        _print_ddl_locations()
        return 1

    passed = sum(1 for result in results if result.status == "pass")
    print(f"\nAll {passed}/{STAGE_COUNT} stages passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
