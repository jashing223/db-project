from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class PetCreate(BaseModel):
    Owner_ID: int
    Pet_Name: str
    Species_Type: str
    Breed_Name: Optional[str] = None
    Birth_Date: Optional[str] = None
    Current_Weight: Optional[float] = None


class PetUpdate(BaseModel):
    Pet_Name: Optional[str] = None
    Species_Type: Optional[str] = None
    Breed_Name: Optional[str] = None
    Birth_Date: Optional[str] = None
    Current_Weight: Optional[float] = None


class PetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Pet_ID: int
    Owner_ID: int
    Pet_Name: str
    Species_Type: str
    Breed_Name: Optional[str] = None
    Birth_Date: Optional[str] = None
    Current_Weight: Optional[float] = None
    Age: Optional[int] = None
