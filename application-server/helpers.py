"""Shared query helpers for enriched appointment responses."""

from __future__ import annotations

from typing import Any

from serialize import serialize_row, serialize_rows

ALL_SLOTS = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]
BUSY_SLOTS: dict[int, list[str]] = {
    1: ["10:00", "14:00"],
    2: ["09:00", "11:00"],
    3: ["13:00"],
}


APPOINTMENT_SELECT = """
    SELECT
        a.Appointment_ID,
        a.Pet_ID,
        a.Doc_Staff_ID,
        a.Scheduled_Time,
        a.Appt_Status,
        p.Pet_ID AS pet_Pet_ID,
        p.Owner_ID AS pet_Owner_ID,
        p.Pet_Name AS pet_Pet_Name,
        p.Species_Type AS pet_Species_Type,
        p.Breed_Name AS pet_Breed_Name,
        p.Birth_Date AS pet_Birth_Date,
        p.Current_Weight AS pet_Current_Weight,
        o.Owner_ID AS owner_Owner_ID,
        o.Full_Name AS owner_Full_Name,
        o.Phone_Number AS owner_Phone_Number,
        o.Email_Address AS owner_Email_Address,
        o.Physical_Address AS owner_Physical_Address,
        o.Is_Anonymized AS owner_Is_Anonymized,
        s.Staff_ID AS doctor_Staff_ID,
        s.Staff_Name AS doctor_Staff_Name,
        s.Role_Level AS doctor_Role_Level,
        d.Specialty AS doctor_Specialty
    FROM Appointments a
    JOIN PetBase p ON a.Pet_ID = p.Pet_ID
    JOIN Owners o ON p.Owner_ID = o.Owner_ID
    JOIN Staff s ON a.Doc_Staff_ID = s.Staff_ID
    JOIN Doctors d ON s.Staff_ID = d.Staff_ID
"""


def _split_prefixed(row: dict[str, Any], prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    plen = len(prefix)
    for key, value in row.items():
        if key.startswith(prefix):
            out[key[plen:]] = value
    return serialize_row(out)  # type: ignore[return-value]


def enrich_appointment(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    base = {
        "Appointment_ID": row["Appointment_ID"],
        "Pet_ID": row["Pet_ID"],
        "Doc_Staff_ID": row["Doc_Staff_ID"],
        "Scheduled_Time": row["Scheduled_Time"],
        "Appt_Status": row["Appt_Status"],
    }
    serialized = serialize_row(base)  # type: ignore[assignment]
    serialized["pet"] = _split_prefixed(row, "pet_")
    serialized["owner"] = _split_prefixed(row, "owner_")
    serialized["doctor"] = _split_prefixed(row, "doctor_")
    return serialized


def enrich_appointments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_appointment(r) for r in rows]  # type: ignore[misc]


def fetch_appointment_by_id(cursor, appointment_id: int) -> dict[str, Any] | None:
    cursor.execute(
        APPOINTMENT_SELECT + " WHERE a.Appointment_ID = %s",
        (appointment_id,),
    )
    return cursor.fetchone()


def fetch_appointments_filtered(cursor, where_sql: str, params: tuple) -> list[dict[str, Any]]:
    cursor.execute(APPOINTMENT_SELECT + " " + where_sql, params)
    return enrich_appointments(cursor.fetchall())
