from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class InvoicePay(BaseModel):
    Payment_Method: Literal["cash", "card", "insurance"]


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Invoice_ID: int
    Record_ID: int
    Total_Billed: float
    Payment_Method: Optional[str] = None
    Payment_Status: int


class InvoicePending(InvoiceOut):
    record: Optional[dict] = None
    pet: Optional[dict] = None
    owner: Optional[dict] = None
