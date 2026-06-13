from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db
from errors import not_found, raise_http_from_db_error
from schemas.owners import OwnerCreate, OwnerUpdate
from serialize import serialize_row, serialize_rows

router = APIRouter(tags=["owners"])

_PET_COLUMNS = """
    Pet_ID, Owner_ID, Pet_Name, Species_Type, Breed_Name,
    Birth_Date, Current_Weight, Age
"""


@router.get("/owners")
def list_owners(conn=Depends(get_db)) -> list[dict]:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM Owners
                WHERE Is_Anonymized = FALSE
                ORDER BY Owner_ID
                """
            )
            owners = cur.fetchall()
            results: list[dict] = []
            for owner_row in owners:
                owner = serialize_row(owner_row)  # type: ignore[assignment]
                cur.execute(
                    f"""
                    SELECT {_PET_COLUMNS}
                    FROM Pets
                    WHERE Owner_ID = %s
                    ORDER BY Pet_ID
                    """,
                    (owner["Owner_ID"],),
                )
                owner["pets"] = serialize_rows(cur.fetchall())
                results.append(owner)
            return results
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

            updates: list[str] = []
            params: list = []
            data = body.model_dump(exclude_unset=True)
            for field in ("Full_Name", "Phone_Number", "Email_Address", "Physical_Address"):
                if field in data:
                    updates.append(f"{field} = %s")
                    params.append(data[field])

            if updates:
                params.append(owner_id)
                cur.execute(
                    f"UPDATE Owners SET {', '.join(updates)} WHERE Owner_ID = %s",
                    tuple(params),
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
