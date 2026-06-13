from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db
from errors import raise_http_from_db_error
from schemas.pets import PetCreate
from serialize import serialize_row, serialize_rows

router = APIRouter(tags=["pets"])


@router.get("/pets")
def list_pets(owner_id: int, conn=Depends(get_db)) -> list[dict]:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT Pet_ID, Owner_ID, Pet_Name, Species_Type, Breed_Name,
                       Birth_Date, Current_Weight, Age
                FROM Pets
                WHERE Owner_ID = %s
                ORDER BY Pet_ID
                """,
                (owner_id,),
            )
            return serialize_rows(cur.fetchall())
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.post("/pets", status_code=201)
def create_pet(body: PetCreate, conn=Depends(get_db)) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO PetBase (Owner_ID, Pet_Name, Species_Type, Breed_Name, Birth_Date, Current_Weight)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    body.Owner_ID,
                    body.Pet_Name,
                    body.Species_Type,
                    body.Breed_Name,
                    body.Birth_Date or None,
                    body.Current_Weight,
                ),
            )
            pet_id = cur.lastrowid
            cur.execute(
                """
                SELECT Pet_ID, Owner_ID, Pet_Name, Species_Type, Breed_Name,
                       Birth_Date, Current_Weight, Age
                FROM Pets WHERE Pet_ID = %s
                """,
                (pet_id,),
            )
            return serialize_row(cur.fetchone())  # type: ignore[return-value]
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}
