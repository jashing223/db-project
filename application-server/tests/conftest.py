"""Shared fixtures for API conformance tests against a live MySQL database."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from check_connection import db_readiness
from db import get_connection
from main import app

APPOINTMENT_PET_FIELDS = {"Pet_ID", "Pet_Name", "Species_Type", "Birth_Date", "Current_Weight"}
APPOINTMENT_OWNER_FIELDS = {"Owner_ID", "Full_Name"}
APPOINTMENT_DOCTOR_FIELDS = {"Staff_ID", "Staff_Name", "Specialty"}
FLAT_APPOINTMENT_FIELDS = {
    "Appointment_ID",
    "Pet_ID",
    "Doc_Staff_ID",
    "Scheduled_Time",
    "Appt_Status",
}

_db_ready, _db_skip_reason = db_readiness()

requires_db = pytest.mark.skipif(
    not _db_ready,
    reason=_db_skip_reason,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_conn():
    with get_connection() as conn:
        yield conn


def insert_staff(db_conn, role_level: int, *, as_doctor: bool = False) -> int:
    suffix = uuid.uuid4().hex[:8]
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO Staff (Staff_Name, Role_Level, Status_Active) VALUES (%s, %s, TRUE)",
            (f"Test Staff {suffix}", role_level),
        )
        staff_id = cur.lastrowid
        if as_doctor or role_level == 3:
            cur.execute(
                "INSERT INTO Doctors (Staff_ID, License_Number, Specialty) VALUES (%s, %s, %s)",
                (staff_id, f"LIC-{suffix}", "Test"),
            )
    db_conn.commit()
    return staff_id


def login_headers(client: TestClient, staff_id: int) -> dict[str, str]:
    response = client.post("/auth/login", json={"Staff_ID": staff_id})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reception_headers(client, db_conn) -> dict[str, str]:
    staff_id = insert_staff(db_conn, 1)
    return login_headers(client, staff_id)


@pytest.fixture
def nurse_headers(client, db_conn) -> dict[str, str]:
    staff_id = insert_staff(db_conn, 2)
    return login_headers(client, staff_id)


@pytest.fixture
def vet_headers(client, db_conn) -> dict[str, str]:
    staff_id = insert_staff(db_conn, 3, as_doctor=True)
    return login_headers(client, staff_id)


@pytest.fixture
def manager_headers(client, db_conn) -> dict[str, str]:
    staff_id = insert_staff(db_conn, 4)
    return login_headers(client, staff_id)


@pytest.fixture
def test_doctor(db_conn) -> int:
    return insert_staff(db_conn, 3, as_doctor=True)


def assert_string_detail(response) -> str:
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)
    return data["detail"]
