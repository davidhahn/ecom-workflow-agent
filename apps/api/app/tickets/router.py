from fastapi import APIRouter, Request, Response

from app.rate_limit import limiter
from app.tickets.schemas import (
    TicketConfirmRequest,
    TicketConfirmResponse,
    TicketDraftRequest,
    TicketDraftResponse,
)
from app.tickets.service import confirm_ticket, draft_ticket

router = APIRouter()


@router.post("/tickets/draft", response_model=TicketDraftResponse)
@limiter.limit("20/hour")
def tickets_draft_endpoint(
    request: Request, response: Response, body: TicketDraftRequest
) -> TicketDraftResponse:
    return draft_ticket(body.request_text)


@router.post("/tickets/confirm", response_model=TicketConfirmResponse)
@limiter.limit("20/hour")
def tickets_confirm_endpoint(
    request: Request, response: Response, body: TicketConfirmRequest
) -> TicketConfirmResponse:
    # The only path that ever writes to support_tickets from user-facing
    # input — see confirm_ticket()'s requires_confirmation enforcement.
    return confirm_ticket(body.draft_id)
