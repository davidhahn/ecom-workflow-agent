from fastapi import APIRouter, Depends, Request, Response

from app.permissions import require_permission
from app.rate_limit import eval_bypass, limiter
from app.tickets.schemas import (
    TicketConfirmRequest,
    TicketConfirmResponse,
    TicketDraftRequest,
    TicketDraftResponse,
)
from app.tickets.service import confirm_ticket, draft_ticket

router = APIRouter()


@router.post("/tickets/draft", response_model=TicketDraftResponse)
@limiter.limit("20/hour", exempt_when=eval_bypass)
def tickets_draft_endpoint(
    request: Request,
    response: Response,
    body: TicketDraftRequest,
    role: str = Depends(require_permission("draft_support_ticket", "ticket_draft")),
) -> TicketDraftResponse:
    return draft_ticket(body.request_text)


@router.post("/tickets/confirm", response_model=TicketConfirmResponse)
@limiter.limit("20/hour", exempt_when=eval_bypass)
def tickets_confirm_endpoint(
    request: Request,
    response: Response,
    body: TicketConfirmRequest,
    role: str = Depends(require_permission("confirm_support_ticket", "ticket_confirm")),
) -> TicketConfirmResponse:
    # The only path that ever writes to support_tickets from user-facing
    # input — see confirm_ticket()'s requires_confirmation enforcement.
    # draft_support_ticket (permission_required="read_only") and
    # confirm_support_ticket (permission_required="write") are looked up as
    # two distinct registry entries by require_permission — this is what
    # actually lets support_agent draft but not confirm, not any special
    # casing here.
    return confirm_ticket(body.draft_id)
