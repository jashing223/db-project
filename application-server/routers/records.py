from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db
from errors import not_found, raise_http_from_db_error
from helpers import verify_drug_stock_for_detail, verify_drug_stock_for_record
from permissions import MEDICAL_WRITE, RECORD_LOCK, require_roles
from schemas.records import DetailCreate, RecordCreate, RecordDraft, RecordLock
from serialize import serialize_row

router = APIRouter(tags=["records"])

_DRAFT_FIELDS = frozenset({"Clinical_Notes", "Final_Diagnosis"})
_LOCK_FIELDS = frozenset({"Clinical_Notes", "Final_Diagnosis"})


def _build_set_clause(data: dict, allowed: frozenset[str]) -> tuple[list[str], list]:
    updates: list[str] = []
    params: list = []
    for field in allowed:
        if field in data:
            updates.append(f"{field} = %s")
            params.append(data[field])
    return updates, params


def _fetch_record(cur, record_id: int, with_details: bool = False) -> dict | None:
    cur.execute("SELECT * FROM Medical_Records WHERE Record_ID = %s", (record_id,))
    row = cur.fetchone()
    if not row:
        return None
    result = serialize_row(row)
    if with_details:
        cur.execute(
            "SELECT * FROM Treatment_Details WHERE Record_ID = %s ORDER BY Detail_ID",
            (record_id,),
        )
        from serialize import serialize_rows

        result["details"] = serialize_rows(cur.fetchall())
    return result


@router.post("/records", status_code=201)
def create_record(
    body: RecordCreate,
    _user=Depends(require_roles(*MEDICAL_WRITE)),
    conn=Depends(get_db),
) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Appointment_ID FROM Appointments WHERE Appointment_ID = %s",
                (body.Appointment_ID,),
            )
            if not cur.fetchone():
                raise not_found("Appointment")

            cur.execute(
                "SELECT Record_ID FROM Medical_Records WHERE Appointment_ID = %s",
                (body.Appointment_ID,),
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Medical record already exists for this appointment")

            cur.execute(
                """
                INSERT INTO Medical_Records (Appointment_ID, Consultation_Date, Clinical_Notes, Final_Diagnosis)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    body.Appointment_ID,
                    body.Consultation_Date,
                    body.Clinical_Notes,
                    body.Final_Diagnosis,
                ),
            )
            record_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO Invoices (Record_ID, Total_Billed, Payment_Status)
                VALUES (%s, 0.00, 0)
                """,
                (record_id,),
            )
            record = _fetch_record(cur, record_id)
            return record  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}


@router.post("/records/{record_id}/details", status_code=201)
def add_detail(
    record_id: int,
    body: DetailCreate,
    _user=Depends(require_roles(*MEDICAL_WRITE)),
    conn=Depends(get_db),
) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Record_ID FROM Medical_Records WHERE Record_ID = %s", (record_id,))
            if not cur.fetchone():
                raise not_found("Medical record")

            verify_drug_stock_for_detail(cur, record_id, body.Item_ID, body.Numeric_Value)

            cur.execute(
                """
                INSERT INTO Treatment_Details
                    (Record_ID, Item_ID, Historical_Price, Numeric_Value, Polymorphic_Text1, Polymorphic_Text2)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    record_id,
                    body.Item_ID,
                    body.Historical_Price,
                    body.Numeric_Value,
                    body.Polymorphic_Text1,
                    body.Polymorphic_Text2,
                ),
            )
            detail_id = cur.lastrowid
            cur.execute("SELECT * FROM Treatment_Details WHERE Detail_ID = %s", (detail_id,))
            return serialize_row(cur.fetchone())  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}


@router.delete("/records/{record_id}/details/{detail_id}")
def delete_detail(
    record_id: int,
    detail_id: int,
    _user=Depends(require_roles(*MEDICAL_WRITE)),
    conn=Depends(get_db),
) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT Detail_ID FROM Treatment_Details
                WHERE Record_ID = %s AND Detail_ID = %s
                """,
                (record_id, detail_id),
            )
            if not cur.fetchone():
                raise not_found("Treatment detail")

            cur.execute(
                "DELETE FROM Treatment_Details WHERE Record_ID = %s AND Detail_ID = %s",
                (record_id, detail_id),
            )
            return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {"ok": False}


@router.patch("/records/{record_id}/draft")
def save_draft(
    record_id: int,
    body: RecordDraft,
    _user=Depends(require_roles(*MEDICAL_WRITE)),
    conn=Depends(get_db),
) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Record_ID FROM Medical_Records WHERE Record_ID = %s", (record_id,))
            if not cur.fetchone():
                raise not_found("Medical record")

            data = body.model_dump(exclude_unset=True)
            updates, params = _build_set_clause(data, _DRAFT_FIELDS)
            if updates:
                params.append(record_id)
                cur.execute(
                    f"UPDATE Medical_Records SET {', '.join(updates)} WHERE Record_ID = %s",
                    tuple(params),
                )

            record = _fetch_record(cur, record_id, with_details=True)
            return record  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}


@router.patch("/records/{record_id}/lock")
def lock_record(
    record_id: int,
    body: RecordLock,
    _user=Depends(require_roles(*RECORD_LOCK)),
    conn=Depends(get_db),
) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Record_ID, Appointment_ID, Record_Locked FROM Medical_Records WHERE Record_ID = %s",
                (record_id,),
            )
            row = cur.fetchone()
            if not row:
                raise not_found("Medical record")
            if row["Record_Locked"]:
                raise HTTPException(status_code=400, detail="Medical record is already locked")

            verify_drug_stock_for_record(cur, record_id)

            data = body.model_dump(exclude_unset=True)
            updates, params = _build_set_clause(data, _LOCK_FIELDS)
            updates.append("Record_Locked = TRUE")
            params.append(record_id)
            cur.execute(
                f"UPDATE Medical_Records SET {', '.join(updates)} WHERE Record_ID = %s",
                tuple(params),
            )
            cur.execute(
                "UPDATE Appointments SET Appt_Status = 2 WHERE Appointment_ID = %s",
                (row["Appointment_ID"],),
            )
            record = _fetch_record(cur, record_id, with_details=True)
            return record  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}
