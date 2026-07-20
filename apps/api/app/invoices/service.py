import uuid
from datetime import datetime, timezone

from sqlalchemy import insert

from app.db.models import VendorInvoice
from app.db.session import SessionLocal
from app.invoices.draft_store import DRAFT_TTL_SECONDS, DraftRecord, create_draft, get_draft, mark_confirmed
from app.invoices.extraction import InvoiceExtractionError, extract_vendor_invoice
from app.invoices.schemas import InvoiceConfirmResponse, InvoiceDraftResponse
from app.invoices.validation import is_duplicate, validate_invoice
from app.observability.logger import request_log_span

COULD_NOT_PROCESS = "could_not_process"


def _confirm_log_output(response: InvoiceConfirmResponse, record: DraftRecord) -> dict:
    """request_log's audit trail for a confirm attempt — not vendor_invoices,
    which a duplicate or an idempotent retry never writes to. Merges the API
    response with the underlying extracted invoice fields from the draft
    record, so a human reviewing /observability/requests can see what was
    actually being confirmed (vendor, invoice number, amounts, line items),
    not just the outcome status, on every branch that reaches this far —
    including a duplicate rejection, which is otherwise the one outcome with
    no corresponding row in vendor_invoices to cross-reference."""
    return {
        **response.model_dump(mode="json"),
        "vendor_name": record.fields["vendor_name"],
        "invoice_number": record.fields["invoice_number"],
        "invoice_date": record.fields["invoice_date"].isoformat(),
        "subtotal_cents": record.fields["subtotal_cents"],
        "tax_cents": record.fields["tax_cents"],
        "total_cents": record.fields["total_cents"],
        "line_items": record.fields["line_items"],
        "field_confidence": record.fields["field_confidence"],
    }


def draft_invoice(image_base64: str, media_type: str) -> InvoiceDraftResponse:
    # Logging a placeholder rather than the raw base64: request_log.input is
    # a TEXT column read by humans/tooling, and an invoice image can be
    # several MB of base64 — not something every row should carry.
    with request_log_span("invoice_draft", f"[invoice image, media_type={media_type}]") as log:
        try:
            extraction = extract_vendor_invoice(image_base64, media_type)
        except InvoiceExtractionError as e:
            response = InvoiceDraftResponse(
                status=COULD_NOT_PROCESS,
                reasoning=f"Could not extract a vendor invoice from the image: {e}",
            )
            log.output = response.model_dump(mode="json")
            return response

        log.add_usage(extraction.usage)

        validation = validate_invoice(
            vendor_name=extraction.vendor_name,
            invoice_number=extraction.invoice_number,
            invoice_date=extraction.invoice_date,
            subtotal_cents=extraction.subtotal_cents,
            tax_cents=extraction.tax_cents,
            total_cents=extraction.total_cents,
            field_confidence=extraction.field_confidence,
        )

        draft_id = create_draft(
            {
                "vendor_name": extraction.vendor_name,
                "invoice_number": extraction.invoice_number,
                "invoice_date": extraction.invoice_date,
                "subtotal_cents": extraction.subtotal_cents,
                "tax_cents": extraction.tax_cents,
                "total_cents": extraction.total_cents,
                "line_items": extraction.line_items,
                "field_confidence": extraction.field_confidence,
                "status": validation.status,
                "flagged_reasons": validation.flagged_reasons,
            }
        )
        response = InvoiceDraftResponse(
            status="drafted",
            draft_id=draft_id,
            vendor_name=extraction.vendor_name,
            invoice_number=extraction.invoice_number,
            invoice_date=extraction.invoice_date,
            subtotal_cents=extraction.subtotal_cents,
            tax_cents=extraction.tax_cents,
            total_cents=extraction.total_cents,
            line_items=extraction.line_items,
            field_confidence=extraction.field_confidence,
            validation_status=validation.status,
            flagged_reasons=validation.flagged_reasons,
            expires_in_seconds=int(DRAFT_TTL_SECONDS),
        )
        log.output = response.model_dump(mode="json")
        return response


def confirm_invoice(draft_id: str) -> InvoiceConfirmResponse:
    with request_log_span("invoice_confirm", draft_id) as log:
        # Import here, not at module scope: app.tools.registry imports from
        # app.invoices.{schemas,tool_spec} to build the registry entries, so
        # importing it back at module scope here would risk a circular
        # import as this package grows — same reasoning as
        # tickets/service.py's confirm_ticket.
        from app.tools.registry import TOOLS

        draft_spec = TOOLS["draft_vendor_invoice"]
        if not draft_spec.requires_confirmation:
            raise RuntimeError(
                "draft_vendor_invoice's registry entry no longer declares "
                "requires_confirmation=True; confirm_invoice's gate is stale "
                "and must be reviewed before this can safely proceed."
            )

        record = get_draft(draft_id)
        if record is None:
            response = InvoiceConfirmResponse(
                status="error",
                error_reason=(
                    f"No pending draft found for draft_id '{draft_id}' "
                    "(not found or already expired)."
                ),
            )
            log.output = response.model_dump(mode="json")
            return response

        if record.confirmed_invoice_id is not None:
            # Idempotent retry: already written once, return the same
            # result rather than inserting a second row.
            response = InvoiceConfirmResponse(
                status="created",
                invoice_id=record.confirmed_invoice_id,
                validation_status=record.fields["status"],
                flagged_reasons=record.fields["flagged_reasons"],
            )
            log.output = _confirm_log_output(response, record)
            return response

        # Re-run the duplicate check here, not just at draft-time — another
        # invoice with the same vendor_name + invoice_number may have been
        # confirmed in between. vendor_invoices has a unique index on that
        # pair, so a duplicate can never be inserted as a second row; the
        # correct move is to refuse the write entirely, the same
        # short-circuit validate_invoice() already applies at draft-time.
        if is_duplicate(record.fields["vendor_name"], record.fields["invoice_number"]):
            response = InvoiceConfirmResponse(
                status="error",
                validation_status="duplicate",
                flagged_reasons=[],
                error_reason=(
                    f"An invoice already exists for vendor "
                    f"'{record.fields['vendor_name']}' with invoice_number "
                    f"'{record.fields['invoice_number']}' — refusing to insert a "
                    "duplicate row."
                ),
            )
            log.output = _confirm_log_output(response, record)
            return response

        # The other checks (arithmetic, date, confidence) were computed
        # against these same extracted fields at draft-time and can't
        # change, so whatever validate_invoice() produced then is what gets
        # persisted now — including a 'flagged' status, since flagging means
        # "needs human review", not "reject and discard".
        status = record.fields["status"]
        flagged_reasons = record.fields["flagged_reasons"]

        invoice_id = uuid.uuid4()
        with SessionLocal() as session:
            session.execute(
                insert(VendorInvoice).values(
                    id=invoice_id,
                    vendor_name=record.fields["vendor_name"],
                    invoice_number=record.fields["invoice_number"],
                    invoice_date=record.fields["invoice_date"],
                    subtotal_cents=record.fields["subtotal_cents"],
                    tax_cents=record.fields["tax_cents"],
                    total_cents=record.fields["total_cents"],
                    line_items=record.fields["line_items"],
                    field_confidence=record.fields["field_confidence"],
                    status=status,
                    flagged_reasons=flagged_reasons,
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

        mark_confirmed(draft_id, invoice_id)

        response = InvoiceConfirmResponse(
            status="created",
            invoice_id=invoice_id,
            validation_status=status,
            flagged_reasons=flagged_reasons,
        )
        log.output = _confirm_log_output(response, record)
        return response
