from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OwnerCreate(BaseModel):
    Full_Name: str
    Phone_Number: Optional[str] = None
    Email_Address: Optional[str] = None
    Physical_Address: Optional[str] = None


class OwnerUpdate(BaseModel):
    Full_Name: Optional[str] = None
    Phone_Number: Optional[str] = None
    Email_Address: Optional[str] = None
    Physical_Address: Optional[str] = None


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Owner_ID: int
    Full_Name: str
    Phone_Number: Optional[str] = None
    Email_Address: Optional[str] = None
    Physical_Address: Optional[str] = None
    Is_Anonymized: bool = False
