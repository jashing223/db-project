from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_db
from errors import conflict, not_found, raise_http_from_db_error
from helpers import ALL_SLOTS, BUSY_SLOTS, fetch_appointment_by_id, fetch_appointments_filtered
from permissions import READ_ALL, RECEPTION_MANAGER, require_roles
from schemas.appointments import AppointmentCreate
from serialize import serialize_row

router = APIRouter(tags=["appointments"])


def _is_slot_available(cur, doctor_id: int, scheduled_time: str) -> bool:
    dt = datetime.fromisoformat(scheduled_time)
    date_str = dt.strftime("%Y-%m-%d")
    slot = dt.strftime("%H:%M")

    if slot not in ALL_SLOTS:
        return False
    if slot in BUSY_SLOTS.get(doctor_id, []):
        return False

    cur.execute(
        """
        SELECT Appointment_ID FROM Appointments
        WHERE Doc_Staff_ID = %s
          AND DATE(Scheduled_Time) = %s
          AND TIME_FORMAT(Scheduled_Time, '%%H:%%i') = %s
          AND Appt_Status != 2
        LIMIT 1
        """,
        (doctor_id, date_str, slot),
    )
    return cur.fetchone() is None


def _flat_appointment(row: dict) -> dict:
    return serialize_row(  # type: ignore[return-value]
        {
            "Appointment_ID": row["Appointment_ID"],
            "Pet_ID": row["Pet_ID"],
            "Doc_Staff_ID": row["Doc_Staff_ID"],
            "Scheduled_Time": row["Scheduled_Time"],
            "Appt_Status": row["Appt_Status"],
        }
    )


@router.post("/appointments", status_code=201)
def create_appointment(
    body: AppointmentCreate,
    _user=Depends(require_roles(*RECEPTION_MANAGER)),
    conn=Depends(get_db),
) -> dict:
    try:
        with conn.cursor() as cur:
            if not _is_slot_available(cur, body.Doc_Staff_ID, body.Scheduled_Time):
                raise conflict("Selected time slot is not available")

            cur.execute(
                """
                INSERT INTO Appointments (Pet_ID, Doc_Staff_ID, Scheduled_Time, Appt_Status)
                VALUES (%s, %s, %s, %s)
                """,
                (body.Pet_ID, body.Doc_Staff_ID, body.Scheduled_Time, body.Appt_Status),
            )
            appt_id = cur.lastrowid
            row = fetch_appointment_by_id(cur, appt_id)
            if not row:
                raise not_found("Appointment")
            return _flat_appointment(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}


@router.get("/appointments/today")
def list_today_appointments(
    _user=Depends(require_roles(*READ_ALL)),
    conn=Depends(get_db),
) -> list[dict]:
    try:
        with conn.cursor() as cur:
            return fetch_appointments_filtered(
                cur,
                "WHERE DATE(a.Scheduled_Time) = CURDATE() AND a.Appt_Status = 0 ORDER BY a.Scheduled_Time",
                (),
            )
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.get("/appointments")
def list_appointments(
    doctor_id: int,
    date: str,
    _user=Depends(require_roles(*READ_ALL)),
    conn=Depends(get_db),
) -> list[dict]:
    try:
        with conn.cursor() as cur:
            return fetch_appointments_filtered(
                cur,
                "WHERE a.Doc_Staff_ID = %s AND DATE(a.Scheduled_Time) = %s ORDER BY a.Scheduled_Time",
                (doctor_id, date),
            )
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []


@router.patch("/appointments/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    _user=Depends(require_roles(*RECEPTION_MANAGER)),
    conn=Depends(get_db),
) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Appointment_ID FROM Appointments WHERE Appointment_ID = %s",
                (appointment_id,),
            )
            if not cur.fetchone():
                raise not_found("Appointment")
            cur.execute(
                "UPDATE Appointments SET Appt_Status = 2 WHERE Appointment_ID = %s",
                (appointment_id,),
            )
            return {"Appointment_ID": appointment_id, "Appt_Status": 2}
    except HTTPException:
        raise
    except Exception as exc:
        raise_http_from_db_error(exc)
        return {}
