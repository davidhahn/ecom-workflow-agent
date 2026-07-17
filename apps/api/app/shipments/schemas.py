import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ShipmentResult(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    carrier: str
    shipped_date: datetime | None
    expected_delivery_date: datetime
    actual_delivery_date: datetime | None
    status: str


class ShipmentStatusResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    shipments: list[ShipmentResult] = []
    row_count: int = 0
    error_reason: str | None = None
