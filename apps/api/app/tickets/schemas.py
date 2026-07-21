import uuid
from typing import Literal

from pydantic import BaseModel


class TicketDraftRequest(BaseModel):
    request_text: str


class TicketDraftResponse(BaseModel):
    status: Literal["drafted", "could_not_process"]
    draft_id: str | None = None
    category: str | None = None
    description: str | None = None
    customer_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    reasoning: str | None = None
    expires_in_seconds: int | None = None
    # Only set when status is "could_not_process" due to unresolvable
    # context: "customer", "product", or both — lets a caller determine
    # exactly what failed without string-parsing `reasoning`.
    unresolved_fields: list[str] | None = None


class TicketConfirmRequest(BaseModel):
    draft_id: str


class TicketConfirmResponse(BaseModel):
    status: Literal["created", "error"]
    ticket_id: uuid.UUID | None = None
    error_reason: str | None = None
