import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel

ValidationStatus = Literal["validated", "flagged", "duplicate"]


class InvoiceDraftRequest(BaseModel):
    image_base64: str
    media_type: Literal["image/jpeg", "image/png"]


class InvoiceDraftResponse(BaseModel):
    status: Literal["drafted", "could_not_process"]
    draft_id: str | None = None
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    subtotal_cents: int | None = None
    tax_cents: int | None = None
    total_cents: int | None = None
    line_items: list[dict[str, Any]] | None = None
    field_confidence: dict[str, float] | None = None
    validation_status: ValidationStatus | None = None
    flagged_reasons: list[str] | None = None
    reasoning: str | None = None
    expires_in_seconds: int | None = None


class InvoiceConfirmRequest(BaseModel):
    draft_id: str


class InvoiceConfirmResponse(BaseModel):
    status: Literal["created", "error"]
    invoice_id: uuid.UUID | None = None
    validation_status: ValidationStatus | None = None
    flagged_reasons: list[str] | None = None
    error_reason: str | None = None
