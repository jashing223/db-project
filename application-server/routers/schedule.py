from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_db
from errors import raise_http_from_db_error
from helpers import ALL_SLOTS, BUSY_SLOTS

router = APIRouter(tags=["schedule"])


@router.get("/schedule")
def get_schedule(doctor_id: int, date: str, conn=Depends(get_db)) -> list[dict]:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT TIME_FORMAT(Scheduled_Time, '%%H:%%i') AS slot_time
                FROM Appointments
                WHERE Doc_Staff_ID = %s
                  AND DATE(Scheduled_Time) = %s
                  AND Appt_Status != 2
                """,
                (doctor_id, date),
            )
            booked = {row["slot_time"] for row in cur.fetchall()}
            busy = set(BUSY_SLOTS.get(doctor_id, []))

            return [
                {
                    "time": slot,
                    "available": slot not in busy and slot not in booked,
                }
                for slot in ALL_SLOTS
            ]
    except Exception as exc:
        raise_http_from_db_error(exc)
        return []
