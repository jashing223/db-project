"""Pydantic models for demo JWT authentication."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    Staff_ID: int = Field(..., ge=1)


class StaffPublic(BaseModel):
    Staff_ID: int
    Staff_Name: str
    Role_Level: int
    Specialty: str | None = None


class CurrentUser(BaseModel):
    Staff_ID: int
    Staff_Name: str
    Role_Level: int
    Specialty: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: StaffPublic
