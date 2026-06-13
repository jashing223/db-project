from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db
from errors import not_found, raise_http_from_db_error
from schemas.owners import OwnerCreate, OwnerOut, OwnerUpdate
from serialize import serialize_row

router = APIRouter(tags=["owners"])


@router.get("/owners/search")
def search_owners(q: str = "", conn=Depends(get_db)) -> list[dict]:
    try:
        with conn.cursor() as cur:
            if q.strip():
                pattern = f"%{q.strip()}%"
                cur.execute(
                    """
                    SELECT * FROM Owners
                    WHERE Is_Anonymized = FALSE
                      AND (Full_Name LIKE %s OR Phone_Number LIKE %s)
                    ORDER BY Owner_ID
                    """,
                    (pattern, pattern),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM Owners
                    WHERE Is_Anonymized = FALSE
                    ORDER BY Owner_ID
                    """
                )
            return [serialize_row(r) for r in cur.fetchall()]  # type: ignore[misc]
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.post("/owners", status_code=201)
def create_owner(body: OwnerCreate, conn=Depends(get_db)) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Owners (Full_Name, Phone_Number, Email_Address, Physical_Address)
                VALUES (%s, %s, %s, %s)
                """,
                (body.Full_Name, body.Phone_Number, body.Email_Address, body.Physical_Address),
            )
            owner_id = cur.lastrowid
            cur.execute("SELECT * FROM Owners WHERE Owner_ID = %s", (owner_id,))
            row = cur.fetchone()
            return serialize_row(row)  # type: ignore[return-value]
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}


@router.patch("/owners/{owner_id}")
def update_owner(owner_id: int, body: OwnerUpdate, conn=Depends(get_db)) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Owner_ID FROM Owners WHERE Owner_ID = %s", (owner_id,))
            if not cur.fetchone():
                raise not_found("Owner")
            cur.execute(
                """
                UPDATE Owners
                SET Full_Name = %s, Phone_Number = %s, Email_Address = %s, Physical_Address = %s
                WHERE Owner_ID = %s
                """,
                (
                    body.Full_Name,
                    body.Phone_Number,
                    body.Email_Address,
                    body.Physical_Address,
                    owner_id,
                ),
            )
            cur.execute("SELECT * FROM Owners WHERE Owner_ID = %s", (owner_id,))
            return serialize_row(cur.fetchone())  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}


@router.patch("/owners/{owner_id}/anonymize")
def anonymize_owner(owner_id: int, conn=Depends(get_db)) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Owner_ID FROM Owners WHERE Owner_ID = %s", (owner_id,))
            if not cur.fetchone():
                raise not_found("Owner")
            phone = f"deleted-{owner_id}-{int(time.time() * 1000)}"
            cur.execute(
                """
                UPDATE Owners
                SET Full_Name = 'Deleted User',
                    Phone_Number = %s,
                    Email_Address = NULL,
                    Physical_Address = NULL,
                    Is_Anonymized = TRUE
                WHERE Owner_ID = %s
                """,
                (phone, owner_id),
            )
            cur.execute("SELECT * FROM Owners WHERE Owner_ID = %s", (owner_id,))
            return serialize_row(cur.fetchone())  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}
