import uuid
from datetime import datetime, timezone

from sqlalchemy import insert

from app.db.models import SupportTicket
from app.db.session import SessionLocal
from app.observability.logger import request_log_span
from app.tickets.draft_store import DRAFT_TTL_SECONDS, create_draft, get_draft, mark_confirmed
from app.tickets.extraction import TicketExtractionError, extract_support_ticket
from app.tickets.resolution import resolve_ticket_context
from app.tickets.schemas import TicketConfirmResponse, TicketDraftResponse

COULD_NOT_PROCESS = "could_not_process"


def draft_ticket(request_text: str) -> TicketDraftResponse:
    with request_log_span("ticket_draft", request_text) as log:
        try:
            extraction = extract_support_ticket(request_text)
        except TicketExtractionError as e:
            response = TicketDraftResponse(
                status=COULD_NOT_PROCESS,
                reasoning=f"Could not extract a support ticket from the text: {e}",
            )
            log.output = response.model_dump(mode="json")
            return response

        log.add_usage(extraction.usage)

        resolved = resolve_ticket_context(extraction.customer_identifier, extraction.product_identifier)
        if resolved is None:
            if not extraction.customer_identifier:
                detail = "no customer could be identified in the request"
            else:
                detail = f"could not resolve customer '{extraction.customer_identifier}'"
                if extraction.product_identifier:
                    detail += f" and product '{extraction.product_identifier}'"
                detail += " against the database"
            response = TicketDraftResponse(
                status=COULD_NOT_PROCESS,
                reasoning=f"Could not resolve enough context to draft a ticket: {detail}.",
            )
            log.output = response.model_dump(mode="json")
            return response

        draft_id = create_draft(
            {
                "customer_id": resolved.customer_id,
                "order_id": resolved.order_id,
                "product_id": resolved.product_id,
                "category": extraction.category,
                "description": extraction.description,
            }
        )
        response = TicketDraftResponse(
            status="drafted",
            draft_id=draft_id,
            category=extraction.category,
            description=extraction.description,
            customer_id=resolved.customer_id,
            order_id=resolved.order_id,
            product_id=resolved.product_id,
            expires_in_seconds=int(DRAFT_TTL_SECONDS),
        )
        log.output = response.model_dump(mode="json")
        return response


def confirm_ticket(draft_id: str) -> TicketConfirmResponse:
    with request_log_span("ticket_confirm", draft_id) as log:
        # Import here, not at module scope: app.tools.registry imports from
        # app.tickets.{schemas,tool_spec} to build the registry entries, so
        # importing it back at module scope here would risk a circular
        # import as this package grows. This is the one read of the
        # registry this module needs, not a general dependency on it.
        from app.tools.registry import TOOLS

        draft_spec = TOOLS["draft_support_ticket"]
        if not draft_spec.requires_confirmation:
            # This function's entire reason to exist is enforcing the gate
            # declared on draft_support_ticket's registry entry — it must
            # not silently keep behaving as if drafts still need confirming
            # if that flag is ever changed out from under it.
            raise RuntimeError(
                "draft_support_ticket's registry entry no longer declares "
                "requires_confirmation=True; confirm_ticket's gate is stale "
                "and must be reviewed before this can safely proceed."
            )

        record = get_draft(draft_id)
        if record is None:
            response = TicketConfirmResponse(
                status="error",
                error_reason=(
                    f"No pending draft found for draft_id '{draft_id}' "
                    "(not found or already expired)."
                ),
            )
            log.output = response.model_dump(mode="json")
            return response

        if record.confirmed_ticket_id is not None:
            # Idempotent retry: already written once, return the same
            # result rather than inserting a second row.
            response = TicketConfirmResponse(status="created", ticket_id=record.confirmed_ticket_id)
            log.output = response.model_dump(mode="json")
            return response

        ticket_id = uuid.uuid4()
        with SessionLocal() as session:
            session.execute(
                insert(SupportTicket).values(
                    id=ticket_id,
                    customer_id=record.fields["customer_id"],
                    order_id=record.fields["order_id"],
                    product_id=record.fields["product_id"],
                    category=record.fields["category"],
                    description=record.fields["description"],
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

        mark_confirmed(draft_id, ticket_id)

        response = TicketConfirmResponse(status="created", ticket_id=ticket_id)
        log.output = response.model_dump(mode="json")
        return response
