"""Demo authentication routes — staff picker and JWT login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import create_access_token
from dependencies import get_db
from errors import not_found, raise_http_from_db_error
from schemas.auth import CurrentUser, LoginRequest, LoginResponse, StaffPublic
from serialize import serialize_rows

router = APIRouter(tags=["auth"])


@router.get("/staff")
def list_staff(conn=Depends(get_db)) -> list[dict]:
    """Public demo staff picker for login UI."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.Staff_ID, s.Staff_Name, s.Role_Level, d.Specialty
                FROM Staff s
                LEFT JOIN Doctors d ON s.Staff_ID = d.Staff_ID
                WHERE s.Status_Active = TRUE
                ORDER BY s.Staff_ID
                """
            )
            return serialize_rows(cur.fetchall())
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.post("/auth/login")
def login(body: LoginRequest, conn=Depends(get_db)) -> LoginResponse:
    """Demo login — accepts Staff_ID only, no password."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.Staff_ID, s.Staff_Name, s.Role_Level, d.Specialty
                FROM Staff s
                LEFT JOIN Doctors d ON s.Staff_ID = d.Staff_ID
                WHERE s.Staff_ID = %s AND s.Status_Active = TRUE
                """,
                (body.Staff_ID,),
            )
            row = cur.fetchone()
            if not row:
                raise not_found("Staff")

            user = CurrentUser(
                Staff_ID=row["Staff_ID"],
                Staff_Name=row["Staff_Name"],
                Role_Level=row["Role_Level"],
                Specialty=row.get("Specialty"),
            )
            token = create_access_token(user)
            return LoginResponse(
                access_token=token,
                user=StaffPublic(
                    Staff_ID=user.Staff_ID,
                    Staff_Name=user.Staff_Name,
                    Role_Level=user.Role_Level,
                    Specialty=user.Specialty,
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return LoginResponse(access_token="", user=StaffPublic(Staff_ID=0, Staff_Name="", Role_Level=0))  # unreachable
