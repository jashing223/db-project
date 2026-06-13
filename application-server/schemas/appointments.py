from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Staff_ID: int
    Staff_Name: str
    Role_Level: int
    Specialty: Optional[str] = None


class SlotOut(BaseModel):
    time: str
    available: bool


class AppointmentCreate(BaseModel):
    Pet_ID: int
    Doc_Staff_ID: int
    Scheduled_Time: str
    Appt_Status: int = 0


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Appointment_ID: int
    Pet_ID: int
    Doc_Staff_ID: int
    Scheduled_Time: str
    Appt_Status: int


class AppointmentEnriched(AppointmentOut):
    pet: Optional[dict] = None
    owner: Optional[dict] = None
    doctor: Optional[dict] = None
