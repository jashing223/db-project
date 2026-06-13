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


@pytest.fixture
def test_doctor(db_conn) -> int:
    suffix = uuid.uuid4().hex[:8]
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO Staff (Staff_Name, Role_Level, Status_Active) VALUES (%s, 3, TRUE)",
            (f"Conformance Doctor {suffix}",),
        )
        staff_id = cur.lastrowid
        cur.execute(
            "INSERT INTO Doctors (Staff_ID, License_Number, Specialty) VALUES (%s, %s, %s)",
            (staff_id, f"LIC-{suffix}", "General"),
        )
    db_conn.commit()
    return staff_id


def assert_string_detail(response) -> str:
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)
    return data["detail"]
