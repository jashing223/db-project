from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db
from errors import not_found, raise_http_from_db_error
from schemas.catalog import CatalogPatch
from serialize import serialize_row, serialize_rows

router = APIRouter(tags=["catalog"])


@router.get("/catalog")
def list_active_catalog(conn=Depends(get_db)) -> list[dict]:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM Catalog_Items
                WHERE Is_Discontinued = FALSE
                ORDER BY Item_ID
                """
            )
            return serialize_rows(cur.fetchall())
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.get("/catalog/all")
def list_all_catalog(conn=Depends(get_db)) -> list[dict]:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM Catalog_Items ORDER BY Item_ID")
            return serialize_rows(cur.fetchall())
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.patch("/catalog/{item_id}")
def patch_catalog(item_id: int, body: CatalogPatch, conn=Depends(get_db)) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Item_ID FROM Catalog_Items WHERE Item_ID = %s", (item_id,))
            if not cur.fetchone():
                raise not_found("Catalog item")

            updates: list[str] = []
            params: list = []
            if body.Current_Price is not None:
                updates.append("Current_Price = %s")
                params.append(body.Current_Price)
            if body.Is_Discontinued is not None:
                updates.append("Is_Discontinued = %s")
                params.append(body.Is_Discontinued)

            if not updates:
                cur.execute("SELECT * FROM Catalog_Items WHERE Item_ID = %s", (item_id,))
                return serialize_row(cur.fetchone())  # type: ignore[return-value]

            params.append(item_id)
            cur.execute(
                f"UPDATE Catalog_Items SET {', '.join(updates)} WHERE Item_ID = %s",
                tuple(params),
            )
            cur.execute("SELECT * FROM Catalog_Items WHERE Item_ID = %s", (item_id,))
            return serialize_row(cur.fetchone())  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}
