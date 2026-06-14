from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db
from errors import not_found, raise_http_from_db_error
from helpers import fetch_pet_owner_for_appointment
from permissions import READ_ALL, RECEPTION_MANAGER, require_roles
from schemas.invoices import InvoicePay
from serialize import serialize_row, serialize_rows

router = APIRouter(tags=["invoices"])

_RECORD_FIELDS = (
    "Record_ID",
    "Consultation_Date",
    "Clinical_Notes",
    "Final_Diagnosis",
    "Record_Locked",
)


def _fetch_pending_record(cur, record_id: int) -> dict | None:
    cur.execute(
        """
        SELECT Record_ID, Consultation_Date, Clinical_Notes, Final_Diagnosis, Record_Locked
        FROM Medical_Records
        WHERE Record_ID = %s
        """,
        (record_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    record = serialize_row(row)
    cur.execute(
        """
        SELECT t.Detail_ID, t.Item_ID, c.Item_Name, t.Numeric_Value, t.Historical_Price
        FROM Treatment_Details t
        JOIN Catalog_Items c ON c.Item_ID = t.Item_ID
        WHERE t.Record_ID = %s
        ORDER BY t.Detail_ID
        """,
        (record_id,),
    )
    record["details"] = serialize_rows(cur.fetchall())
    return record


@router.get("/invoices/pending")
def list_pending_invoices(
    _user=Depends(require_roles(*READ_ALL)),
    conn=Depends(get_db),
) -> list[dict]:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT i.*
                FROM Invoices i
                JOIN Medical_Records mr ON i.Record_ID = mr.Record_ID
                WHERE i.Payment_Status = 0 AND mr.Record_Locked = TRUE
                ORDER BY i.Invoice_ID
                """
            )
            invoices = cur.fetchall()
            results: list[dict] = []

            for inv_row in invoices:
                inv = serialize_row(inv_row)
                record = _fetch_pending_record(cur, inv["Record_ID"])
                if not record:
                    continue

                cur.execute(
                    "SELECT Appointment_ID FROM Medical_Records WHERE Record_ID = %s",
                    (inv["Record_ID"],),
                )
                mr = cur.fetchone()
                pet, owner = (
                    fetch_pet_owner_for_appointment(cur, mr["Appointment_ID"])
                    if mr
                    else (None, None)
                )

                inv["record"] = record
                inv["pet"] = pet
                inv["owner"] = owner
                results.append(inv)

            return results
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.patch("/invoices/{invoice_id}/pay")
def pay_invoice(
    invoice_id: int,
    body: InvoicePay,
    _user=Depends(require_roles(*RECEPTION_MANAGER)),
    conn=Depends(get_db),
) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Invoice_ID, Payment_Status FROM Invoices WHERE Invoice_ID = %s",
                (invoice_id,),
            )
            row = cur.fetchone()
            if not row:
                raise not_found("Invoice")
            if row["Payment_Status"] != 0:
                raise HTTPException(status_code=400, detail="Invoice is already paid or not payable")

            cur.execute(
                """
                UPDATE Invoices
                SET Payment_Status = 1, Payment_Method = %s
                WHERE Invoice_ID = %s
                """,
                (body.Payment_Method, invoice_id),
            )
            cur.execute("SELECT * FROM Invoices WHERE Invoice_ID = %s", (invoice_id,))
            return serialize_row(cur.fetchone())  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}
