from fastapi import APIRouter, Depends, Request, Response

from app.invoices.schemas import (
    InvoiceConfirmRequest,
    InvoiceConfirmResponse,
    InvoiceDraftRequest,
    InvoiceDraftResponse,
)
from app.invoices.service import confirm_invoice, draft_invoice
from app.permissions import require_permission
from app.rate_limit import limiter

router = APIRouter()


@router.post("/invoices/draft", response_model=InvoiceDraftResponse)
@limiter.limit("20/hour")
def invoices_draft_endpoint(
    request: Request,
    response: Response,
    body: InvoiceDraftRequest,
    role: str = Depends(require_permission("draft_vendor_invoice", "invoice_draft")),
) -> InvoiceDraftResponse:
    return draft_invoice(body.image_base64, body.media_type)


@router.post("/invoices/confirm", response_model=InvoiceConfirmResponse)
@limiter.limit("20/hour")
def invoices_confirm_endpoint(
    request: Request,
    response: Response,
    body: InvoiceConfirmRequest,
    role: str = Depends(require_permission("confirm_vendor_invoice", "invoice_confirm")),
) -> InvoiceConfirmResponse:
    # The only path that ever writes to vendor_invoices from user-facing
    # input — see confirm_invoice()'s requires_confirmation enforcement.
    # draft_vendor_invoice (permission_required="read_only") and
    # confirm_vendor_invoice (permission_required="write") are looked up as
    # two distinct registry entries by require_permission — same split as
    # the ticket draft/confirm flow.
    return confirm_invoice(body.draft_id)
