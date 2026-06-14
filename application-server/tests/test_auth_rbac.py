"""Role-based access control tests — require a running MySQL instance with schema applied."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import (
    assert_string_detail,
    insert_staff,
    login_headers,
    requires_db,
)

pytestmark = requires_db


def test_protected_route_without_token(client):
    response = client.get("/owners")
    assert response.status_code == 401
    assert_string_detail(response)


def test_login_inactive_staff(client, db_conn):
    staff_id = insert_staff(db_conn, 1)
    with db_conn.cursor() as cur:
        cur.execute("UPDATE Staff SET Status_Active = FALSE WHERE Staff_ID = %s", (staff_id,))
    db_conn.commit()

    response = client.post("/auth/login", json={"Staff_ID": staff_id})
    assert response.status_code == 404
    assert_string_detail(response)


def test_login_valid_staff(client, db_conn):
    staff_id = insert_staff(db_conn, 1)
    response = client.post("/auth/login", json={"Staff_ID": staff_id})
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    user = data["user"]
    assert user["Staff_ID"] == staff_id
    assert user["Role_Level"] == 1
    assert "Staff_Name" in user


def test_role1_cannot_patch_catalog(client, reception_headers, db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO Catalog_Items (Item_Name, Item_Category, Current_Price, Stock_Quantity)
            VALUES ('RBAC Test Item', 1, 10.00, 100)
            """
        )
        item_id = cur.lastrowid
    db_conn.commit()

    response = client.patch(
        f"/catalog/{item_id}",
        json={"Current_Price": 15.00},
        headers=reception_headers,
    )
    assert response.status_code == 403
    assert_string_detail(response)


def test_role4_can_patch_catalog(client, manager_headers, db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO Catalog_Items (Item_Name, Item_Category, Current_Price, Stock_Quantity)
            VALUES ('RBAC Manager Item', 1, 10.00, 100)
            """
        )
        item_id = cur.lastrowid
    db_conn.commit()

    response = client.patch(
        f"/catalog/{item_id}",
        json={"Current_Price": 15.00},
        headers=manager_headers,
    )
    assert response.status_code == 200
    assert response.json()["Current_Price"] == 15.0


def _create_record_for_lock(client, test_doctor, reception_headers, medical_headers):
    suffix = uuid.uuid4().hex[:8]
    owner = client.post(
        "/owners",
        json={"Full_Name": f"Lock Owner {suffix}", "Phone_Number": f"0955-{suffix[:4]}-{suffix[4:8]}"},
        headers=reception_headers,
    ).json()
    pet = client.post(
        "/pets",
        json={"Owner_ID": owner["Owner_ID"], "Pet_Name": "LockPet", "Species_Type": "貓"},
        headers=reception_headers,
    ).json()
    appt = client.post(
        "/appointments",
        json={
            "Pet_ID": pet["Pet_ID"],
            "Doc_Staff_ID": test_doctor,
            "Scheduled_Time": "2099-01-15T15:00:00",
            "Appt_Status": 0,
        },
        headers=reception_headers,
    ).json()
    record = client.post(
        "/records",
        json={"Appointment_ID": appt["Appointment_ID"], "Consultation_Date": "2099-01-15"},
        headers=medical_headers,
    ).json()
    return record["Record_ID"]


def test_role2_can_lock_record(client, reception_headers, nurse_headers, vet_headers, test_doctor):
    record_id = _create_record_for_lock(client, test_doctor, reception_headers, nurse_headers)
    response = client.patch(
        f"/records/{record_id}/lock",
        json={"Clinical_Notes": "test", "Final_Diagnosis": "test", "Record_Locked": True},
        headers=nurse_headers,
    )
    assert response.status_code == 200
    assert response.json()["Record_Locked"] is True


def test_role4_cannot_lock_record(client, reception_headers, manager_headers, vet_headers, test_doctor):
    record_id = _create_record_for_lock(client, test_doctor, reception_headers, manager_headers)
    response = client.patch(
        f"/records/{record_id}/lock",
        json={"Clinical_Notes": "test", "Final_Diagnosis": "test", "Record_Locked": True},
        headers=manager_headers,
    )
    assert response.status_code == 403
    assert_string_detail(response)


def test_role3_can_lock_record(client, reception_headers, vet_headers, test_doctor):
    record_id = _create_record_for_lock(client, test_doctor, reception_headers, vet_headers)
    response = client.patch(
        f"/records/{record_id}/lock",
        json={"Clinical_Notes": "test", "Final_Diagnosis": "test", "Record_Locked": True},
        headers=vet_headers,
    )
    assert response.status_code == 200
    assert response.json()["Record_Locked"] is True


def test_role3_cannot_pay_invoice(client, vet_headers):
    response = client.patch(
        "/invoices/999999/pay",
        json={"Payment_Method": "cash"},
        headers=vet_headers,
    )
    assert response.status_code == 403
    assert_string_detail(response)


def test_role1_can_attempt_pay_invoice(client, reception_headers):
    response = client.patch(
        "/invoices/999999/pay",
        json={"Payment_Method": "cash"},
        headers=reception_headers,
    )
    assert response.status_code == 404
    assert_string_detail(response)
