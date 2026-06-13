from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class RecordCreate(BaseModel):
    Appointment_ID: int
    Consultation_Date: str
    Clinical_Notes: Optional[str] = None
    Final_Diagnosis: Optional[str] = None


class DetailCreate(BaseModel):
    Item_ID: int
    Numeric_Value: float
    Historical_Price: float = 0
    Polymorphic_Text1: Optional[str] = None
    Polymorphic_Text2: Optional[str] = None


class RecordDraft(BaseModel):
    Clinical_Notes: Optional[str] = None
    Final_Diagnosis: Optional[str] = None


class RecordLock(BaseModel):
    Clinical_Notes: Optional[str] = None
    Final_Diagnosis: Optional[str] = None
    Record_Locked: bool = True


class DetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Detail_ID: int
    Record_ID: int
    Item_ID: int
    Historical_Price: float
    Numeric_Value: float
    Polymorphic_Text1: Optional[str] = None
    Polymorphic_Text2: Optional[str] = None


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Record_ID: int
    Appointment_ID: int
    Consultation_Date: str
    Clinical_Notes: Optional[str] = None
    Final_Diagnosis: Optional[str] = None
    Record_Locked: bool = False
    details: list[dict] = []
