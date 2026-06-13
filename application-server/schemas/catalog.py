from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class CatalogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Item_ID: int
    Item_Name: str
    Item_Category: int
    Current_Price: float
    Stock_Quantity: Optional[int] = None
    Is_Discontinued: bool = False


class CatalogPatch(BaseModel):
    Current_Price: Optional[float] = None
    Is_Discontinued: Optional[bool] = None
