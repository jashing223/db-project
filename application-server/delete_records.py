#!/usr/bin/env python3
"""Delete clinical and client data from MySQL.

Removes rows from (in FK-safe order):
  Invoices, Medical_Records, Appointments, PetBase, Owners, Catalog_Items, Staff

Treatment_Details are removed automatically when Medical_Records are deleted (FK CASCADE).
Doctors are removed automatically when Staff are deleted (FK CASCADE).
"""

from __future__ import annotations

import argparse
import sys

from db import get_connection


def _placeholders(count: int) -> str:
    return ", ".join(["%s"] * count)


def delete_all() -> dict[str, int]:
    steps = [
        ("invoices", "DELETE FROM Invoices"),
        ("medical_records", "DELETE FROM Medical_Records"),
        ("appointments", "DELETE FROM Appointments"),
        ("pets", "DELETE FROM PetBase"),
        ("owners", "DELETE FROM Owners"),
        ("catalog_items", "DELETE FROM Catalog_Items"),
        ("staff", "DELETE FROM Staff"),
    ]
    counts: dict[str, int] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            for key, sql in steps:
                cur.execute(sql)
                counts[key] = cur.rowcount
    return counts


def delete_records(record_ids: list[int]) -> dict[str, int]:
    counts: dict[str, int] = {
        "invoices": 0,
        "medical_records": 0,
        "appointments": 0,
        "pets": 0,
        "owners": 0,
        "catalog_items": 0,
        "staff": 0,
    }
    with get_connection() as conn:
        with conn.cursor() as cur:
            ph = _placeholders(len(record_ids))
            cur.execute(
                f"SELECT Record_ID, Appointment_ID FROM Medical_Records WHERE Record_ID IN ({ph})",
                tuple(record_ids),
            )
            rows = cur.fetchall()
            if not rows:
                return counts

            matched_record_ids = [row["Record_ID"] for row in rows]
            appt_ids = [row["Appointment_ID"] for row in rows]

            cur.execute(
                f"SELECT Item_ID FROM Treatment_Details WHERE Record_ID IN ({ph})",
                tuple(record_ids),
            )
            item_ids = {row["Item_ID"] for row in cur.fetchall()}

            ph_appt = _placeholders(len(appt_ids))
            cur.execute(
                f"SELECT Appointment_ID, Pet_ID, Doc_Staff_ID FROM Appointments WHERE Appointment_ID IN ({ph_appt})",
                tuple(appt_ids),
            )
            appt_rows = cur.fetchall()
            pet_ids = [row["Pet_ID"] for row in appt_rows]
            doc_staff_ids = {row["Doc_Staff_ID"] for row in appt_rows}

            owner_ids: set[int] = set()
            if pet_ids:
                ph_pets = _placeholders(len(pet_ids))
                cur.execute(
                    f"SELECT Owner_ID FROM PetBase WHERE Pet_ID IN ({ph_pets})",
                    tuple(pet_ids),
                )
                owner_ids = {row["Owner_ID"] for row in cur.fetchall()}

            ph_records = _placeholders(len(matched_record_ids))
            cur.execute(
                f"DELETE FROM Invoices WHERE Record_ID IN ({ph_records})",
                tuple(matched_record_ids),
            )
            counts["invoices"] = cur.rowcount

            cur.execute(
                f"DELETE FROM Medical_Records WHERE Record_ID IN ({ph_records})",
                tuple(matched_record_ids),
            )
            counts["medical_records"] = cur.rowcount

            cur.execute(
                f"DELETE FROM Appointments WHERE Appointment_ID IN ({ph_appt})",
                tuple(appt_ids),
            )
            counts["appointments"] = cur.rowcount

            orphan_pets = []
            for pet_id in pet_ids:
                cur.execute("SELECT 1 FROM Appointments WHERE Pet_ID = %s LIMIT 1", (pet_id,))
                if not cur.fetchone():
                    orphan_pets.append(pet_id)

            if orphan_pets:
                ph_orphan_pets = _placeholders(len(orphan_pets))
                cur.execute(
                    f"DELETE FROM PetBase WHERE Pet_ID IN ({ph_orphan_pets})",
                    tuple(orphan_pets),
                )
                counts["pets"] = cur.rowcount

            orphan_owners = []
            for owner_id in owner_ids:
                cur.execute("SELECT 1 FROM PetBase WHERE Owner_ID = %s LIMIT 1", (owner_id,))
                if not cur.fetchone():
                    orphan_owners.append(owner_id)
            if orphan_owners:
                ph_orphan_owners = _placeholders(len(orphan_owners))
                cur.execute(
                    f"DELETE FROM Owners WHERE Owner_ID IN ({ph_orphan_owners})",
                    tuple(orphan_owners),
                )
                counts["owners"] = cur.rowcount

            orphan_items = []
            for item_id in item_ids:
                cur.execute(
                    "SELECT 1 FROM Treatment_Details WHERE Item_ID = %s LIMIT 1",
                    (item_id,),
                )
                if not cur.fetchone():
                    orphan_items.append(item_id)
            if orphan_items:
                ph_orphan_items = _placeholders(len(orphan_items))
                cur.execute(
                    f"DELETE FROM Catalog_Items WHERE Item_ID IN ({ph_orphan_items})",
                    tuple(orphan_items),
                )
                counts["catalog_items"] = cur.rowcount

            orphan_staff = []
            for staff_id in doc_staff_ids:
                cur.execute(
                    "SELECT 1 FROM Appointments WHERE Doc_Staff_ID = %s LIMIT 1",
                    (staff_id,),
                )
                if not cur.fetchone():
                    orphan_staff.append(staff_id)
            if orphan_staff:
                ph_orphan_staff = _placeholders(len(orphan_staff))
                cur.execute(
                    f"DELETE FROM Staff WHERE Staff_ID IN ({ph_orphan_staff})",
                    tuple(orphan_staff),
                )
                counts["staff"] = cur.rowcount

    return counts


def _print_counts(counts: dict[str, int]) -> None:
    labels = {
        "invoices": "invoice(s)",
        "medical_records": "medical record(s)",
        "appointments": "appointment(s)",
        "pets": "pet(s)",
        "owners": "owner(s)",
        "catalog_items": "catalog item(s)",
        "staff": "staff member(s)",
    }
    for key, label in labels.items():
        print(f"Deleted {counts.get(key, 0)} {label}.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete clinical/client data from MySQL (records, appointments, pets, owners, catalog, staff)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Delete all rows in these tables")
    group.add_argument(
        "--record-id",
        type=int,
        action="append",
        dest="record_ids",
        metavar="ID",
        help="Delete record(s) and related rows (repeatable)",
    )
    args = parser.parse_args()

    try:
        counts = delete_all() if args.all else delete_records(args.record_ids)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_counts(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
