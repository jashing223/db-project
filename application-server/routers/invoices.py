from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db
from errors import not_found, raise_http_from_db_error
from helpers import enrich_appointment, fetch_appointment_by_id
from schemas.invoices import InvoicePay
from serialize import serialize_row, serialize_rows

router = APIRouter(tags=["invoices"])


def _fetch_record_with_details(cur, record_id: int) -> dict | None:
    cur.execute("SELECT * FROM Medical_Records WHERE Record_ID = %s", (record_id,))
    row = cur.fetchone()
    if not row:
        return None
    record = serialize_row(row)
    cur.execute(
        "SELECT * FROM Treatment_Details WHERE Record_ID = %s ORDER BY Detail_ID",
        (record_id,),
    )
    record["details"] = serialize_rows(cur.fetchall())
    return record


@router.get("/invoices/pending")
def list_pending_invoices(conn=Depends(get_db)) -> list[dict]:
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
                record = _fetch_record_with_details(cur, inv["Record_ID"])
                if not record:
                    continue

                cur.execute(
                    "SELECT Appointment_ID FROM Medical_Records WHERE Record_ID = %s",
                    (inv["Record_ID"],),
                )
                mr = cur.fetchone()
                appt_row = fetch_appointment_by_id(cur, mr["Appointment_ID"]) if mr else None
                appt = enrich_appointment(appt_row) if appt_row else None

                inv["record"] = record
                inv["appt"] = appt
                inv["pet"] = appt.get("pet") if appt else None
                inv["owner"] = appt.get("owner") if appt else None
                results.append(inv)

            return results
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.patch("/invoices/{invoice_id}/pay")
def pay_invoice(invoice_id: int, body: InvoicePay, conn=Depends(get_db)) -> dict:
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
