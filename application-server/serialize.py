"""Convert DB rows to JSON-friendly dicts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

BOOLEAN_COLUMNS = frozenset({
    "Is_Anonymized",
    "Is_Discontinued",
    "Record_Locked",
    "Status_Active",
})


def serialize_value(value: Any, key: str | None = None) -> Any:
    if value is None:
        return None
    if key in BOOLEAN_COLUMNS and isinstance(value, (bool, int)):
        return bool(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def serialize_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: serialize_value(v, k) for k, v in row.items()}


def serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialize_row(r) for r in rows]  # type: ignore[misc]
