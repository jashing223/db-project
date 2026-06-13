"""Shared query helpers for enriched appointment responses."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from errors import bad_request
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


def _aggregated_drug_quantities(cursor, record_id: int) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT t.Item_ID, c.Item_Name, SUM(t.Numeric_Value) AS total_qty
        FROM Treatment_Details t
        JOIN Catalog_Items c ON c.Item_ID = t.Item_ID
        WHERE t.Record_ID = %s AND c.Item_Category = 1
        GROUP BY t.Item_ID, c.Item_Name
        ORDER BY t.Item_ID
        """,
        (record_id,),
    )
    return cursor.fetchall()


def _as_number(value: Decimal | float | int) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def verify_drug_stock_for_detail(
    cursor,
    record_id: int,
    item_id: int,
    numeric_value: float,
) -> None:
    """Ensure adding a drug detail would not exceed current catalog stock."""
    cursor.execute(
        """
        SELECT Item_ID, Item_Name, Item_Category
        FROM Catalog_Items
        WHERE Item_ID = %s
        """,
        (item_id,),
    )
    item = cursor.fetchone()
    if not item:
        raise bad_request("Catalog item not found")
    if item["Item_Category"] != 1:
        return

    cursor.execute(
        """
        SELECT COALESCE(SUM(Numeric_Value), 0) AS existing_qty
        FROM Treatment_Details
        WHERE Record_ID = %s AND Item_ID = %s
        """,
        (record_id, item_id),
    )
    existing_qty = _as_number(cursor.fetchone()["existing_qty"])
    total_needed = existing_qty + numeric_value

    cursor.execute(
        """
        SELECT Stock_Quantity
        FROM Catalog_Items
        WHERE Item_ID = %s AND Item_Category = 1
        FOR UPDATE
        """,
        (item_id,),
    )
    catalog = cursor.fetchone()
    if catalog is None or _as_number(catalog["Stock_Quantity"]) < total_needed:
        raise bad_request(f"Insufficient stock for item {item['Item_Name']}")


def verify_drug_stock_for_record(cursor, record_id: int) -> None:
    """Ensure aggregated drug quantities for a record do not exceed current stock."""
    for row in _aggregated_drug_quantities(cursor, record_id):
        item_id = row["Item_ID"]
        total_qty = _as_number(row["total_qty"])
        item_name = row["Item_Name"]

        cursor.execute(
            """
            SELECT Stock_Quantity
            FROM Catalog_Items
            WHERE Item_ID = %s AND Item_Category = 1
            FOR UPDATE
            """,
            (item_id,),
        )
        catalog = cursor.fetchone()
        if catalog is None or _as_number(catalog["Stock_Quantity"]) < total_qty:
            raise bad_request(f"Insufficient stock for item {item_name}")
