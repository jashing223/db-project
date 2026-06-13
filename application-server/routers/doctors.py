from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_db
from errors import raise_http_from_db_error
from serialize import serialize_rows

router = APIRouter(tags=["doctors"])


@router.get("/doctors")
def list_doctors(conn=Depends(get_db)) -> list[dict]:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.Staff_ID, s.Staff_Name, s.Role_Level, d.Specialty
                FROM Staff s
                JOIN Doctors d ON s.Staff_ID = d.Staff_ID
                WHERE s.Role_Level = 3 AND s.Status_Active = TRUE
                ORDER BY s.Staff_ID
                """
            )
            return serialize_rows(cur.fetchall())
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []
