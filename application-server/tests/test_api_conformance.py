"""API conformance tests — require a running MySQL instance with schema applied."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import (
    APPOINTMENT_DOCTOR_FIELDS,
    APPOINTMENT_OWNER_FIELDS,
    APPOINTMENT_PET_FIELDS,
    FLAT_APPOINTMENT_FIELDS,
    assert_string_detail,
    requires_db,
)

pytestmark = requires_db


def test_owners_search_removed(client):
    response = client.get("/owners/search")
    assert response.status_code in (404, 405)


def test_get_owners_structure(client):
    response = client.get("/owners")
    assert response.status_code == 200
    owners = response.json()
    assert isinstance(owners, list)
    for owner in owners:
        assert owner.get("Is_Anonymized") is False
        assert "pets" in owner
        assert isinstance(owner["pets"], list)
        for pet in owner["pets"]:
            assert "Age" in pet
            assert pet["Owner_ID"] == owner["Owner_ID"]


def test_patch_owner_single_field(client):
    suffix = uuid.uuid4().hex[:8]
    create = client.post(
        "/owners",
        json={
            "Full_Name": f"Conformance Owner {suffix}",
            "Phone_Number": f"0900-{suffix[:4]}-{suffix[4:8]}",
        },
    )
    assert create.status_code == 201
    owner = create.json()
    owner_id = owner["Owner_ID"]
    original_name = owner["Full_Name"]
    new_phone = f"0933-{suffix[:4]}-{suffix[4:8]}"

    patch = client.patch(f"/owners/{owner_id}", json={"Phone_Number": new_phone})
    assert patch.status_code == 200
    updated = patch.json()
    assert updated["Phone_Number"] == new_phone
    assert updated["Full_Name"] == original_name


def test_patch_pet_weight_only(client):
    suffix = uuid.uuid4().hex[:8]
    owner = client.post(
        "/owners",
        json={"Full_Name": f"Pet Owner {suffix}", "Phone_Number": f"0911-{suffix[:4]}-{suffix[4:8]}"},
    ).json()
    pet = client.post(
        "/pets",
        json={
            "Owner_ID": owner["Owner_ID"],
            "Pet_Name": "TestPet",
            "Species_Type": "犬",
            "Current_Weight": 5.0,
        },
    ).json()
    pet_id = pet["Pet_ID"]

    patch = client.patch(f"/pets/{pet_id}", json={"Current_Weight": 9.1})
    assert patch.status_code == 200
    updated = patch.json()
    assert updated["Current_Weight"] == 9.1
    assert updated["Pet_Name"] == "TestPet"
    assert "Age" in updated


def test_post_appointment_flat_response(client, test_doctor):
    suffix = uuid.uuid4().hex[:8]
    owner = client.post(
        "/owners",
        json={"Full_Name": f"Appt Owner {suffix}", "Phone_Number": f"0922-{suffix[:4]}-{suffix[4:8]}"},
    ).json()
    pet = client.post(
        "/pets",
        json={"Owner_ID": owner["Owner_ID"], "Pet_Name": "ApptPet", "Species_Type": "貓"},
    ).json()

    response = client.post(
        "/appointments",
        json={
            "Pet_ID": pet["Pet_ID"],
            "Doc_Staff_ID": test_doctor,
            "Scheduled_Time": "2099-12-31T15:00:00",
            "Appt_Status": 0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert set(data.keys()) == FLAT_APPOINTMENT_FIELDS
    assert "pet" not in data
    assert "owner" not in data
    assert "doctor" not in data


def test_get_appointments_today_nested_fields(client):
    response = client.get("/appointments/today")
    assert response.status_code == 200
    for appt in response.json():
        assert set(appt["pet"].keys()) == APPOINTMENT_PET_FIELDS
        assert set(appt["owner"].keys()) == APPOINTMENT_OWNER_FIELDS
        assert set(appt["doctor"].keys()) == APPOINTMENT_DOCTOR_FIELDS


def test_cancel_appointment_response(client, test_doctor):
    suffix = uuid.uuid4().hex[:8]
    owner = client.post(
        "/owners",
        json={"Full_Name": f"Cancel Owner {suffix}", "Phone_Number": f"0933-{suffix[:4]}-{suffix[4:8]}"},
    ).json()
    pet = client.post(
        "/pets",
        json={"Owner_ID": owner["Owner_ID"], "Pet_Name": "CancelPet", "Species_Type": "貓"},
    ).json()

    appt = client.post(
        "/appointments",
        json={
            "Pet_ID": pet["Pet_ID"],
            "Doc_Staff_ID": test_doctor,
            "Scheduled_Time": "2099-11-30T16:00:00",
            "Appt_Status": 0,
        },
    ).json()
    appt_id = appt["Appointment_ID"]

    cancel = client.patch(f"/appointments/{appt_id}/cancel")
    assert cancel.status_code == 200
    data = cancel.json()
    assert set(data.keys()) == {"Appointment_ID", "Appt_Status"}
    assert data["Appointment_ID"] == appt_id
    assert data["Appt_Status"] == 2


def test_get_pending_invoices_shape(client):
    response = client.get("/invoices/pending")
    assert response.status_code == 200
    for inv in response.json():
        assert "appt" not in inv
        record = inv.get("record")
        if record and record.get("details"):
            for detail in record["details"]:
                assert "Item_Name" in detail
                assert set(detail.keys()) == {
                    "Detail_ID",
                    "Item_ID",
                    "Item_Name",
                    "Numeric_Value",
                    "Historical_Price",
                }
        if inv.get("pet"):
            assert set(inv["pet"].keys()) == {"Pet_ID", "Pet_Name", "Species_Type"}
        if inv.get("owner"):
            assert set(inv["owner"].keys()) == {"Owner_ID", "Full_Name"}


def test_pay_invoice_invalid_method(client):
    response = client.patch("/invoices/999999/pay", json={"Payment_Method": "bitcoin"})
    assert response.status_code == 422
    assert_string_detail(response)


def test_get_doctors_no_role_level(client):
    response = client.get("/doctors")
    assert response.status_code == 200
    for doctor in response.json():
        assert set(doctor.keys()) == {"Staff_ID", "Staff_Name", "Specialty"}
        assert "Role_Level" not in doctor


def test_error_format_not_found(client):
    response = client.get("/pets?owner_id=999999999")
    assert response.status_code == 200  # empty list is valid

    response = client.patch("/owners/999999999", json={"Phone_Number": "000"})
    assert response.status_code == 404
    assert_string_detail(response)


def test_validation_error_string_detail(client):
    response = client.post("/owners", json={"Phone_Number": "missing name"})
    assert response.status_code == 422
    assert_string_detail(response)


def test_post_record_no_details_key(client, test_doctor):
    suffix = uuid.uuid4().hex[:8]
    owner = client.post(
        "/owners",
        json={"Full_Name": f"Record Owner {suffix}", "Phone_Number": f"0944-{suffix[:4]}-{suffix[4:8]}"},
    ).json()
    pet = client.post(
        "/pets",
        json={"Owner_ID": owner["Owner_ID"], "Pet_Name": "RecordPet", "Species_Type": "犬"},
    ).json()

    appt = client.post(
        "/appointments",
        json={
            "Pet_ID": pet["Pet_ID"],
            "Doc_Staff_ID": test_doctor,
            "Scheduled_Time": "2099-06-01T15:00:00",
            "Appt_Status": 0,
        },
    ).json()

    record = client.post(
        "/records",
        json={
            "Appointment_ID": appt["Appointment_ID"],
            "Consultation_Date": "2099-06-01",
        },
    )
    assert record.status_code == 201
    data = record.json()
    assert "details" not in data
