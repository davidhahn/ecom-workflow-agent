"""Deterministic, non-LLM validation for a drafted vendor invoice. The
duplicate check is the one rule that touches the database (an existing-row
lookup, not a heuristic) — everything else here is pure Python over the
extracted fields."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import VendorInvoice
from app.db.session import SessionLocal
from app.invoices.schemas import ValidationStatus

CONFIDENCE_THRESHOLD = 0.7
DOLLAR_FIELDS = ("subtotal_cents", "tax_cents", "total_cents")
MAX_PAST_INVOICE_AGE = timedelta(days=365 * 2)


@dataclass
class ValidationResult:
    status: ValidationStatus
    flagged_reasons: list[str]


def is_duplicate(vendor_name: str, invoice_number: str) -> bool:
    with SessionLocal() as session:
        existing_id = session.execute(
            select(VendorInvoice.id).where(
                VendorInvoice.vendor_name == vendor_name,
                VendorInvoice.invoice_number == invoice_number,
            )
        ).scalars().first()
    return existing_id is not None


def validate_invoice(
    *,
    vendor_name: str,
    invoice_number: str,
    invoice_date: date,
    subtotal_cents: int,
    tax_cents: int,
    total_cents: int,
    field_confidence: dict[str, float],
) -> ValidationResult:
    # Most important check: short-circuits everything else. A duplicate must
    # never slip through even if every other check would have passed.
    if is_duplicate(vendor_name, invoice_number):
        return ValidationResult(status="duplicate", flagged_reasons=[])

    flagged_reasons: list[str] = []

    if subtotal_cents + tax_cents != total_cents:
        flagged_reasons.append(
            f"subtotal_cents ({subtotal_cents}) + tax_cents ({tax_cents}) != "
            f"total_cents ({total_cents})"
        )

    today = datetime.now(timezone.utc).date()
    if invoice_date > today:
        flagged_reasons.append(f"invoice_date ({invoice_date}) is in the future")
    elif today - invoice_date > MAX_PAST_INVOICE_AGE:
        flagged_reasons.append(
            f"invoice_date ({invoice_date}) is more than 2 years in the past"
        )

    for field_name in DOLLAR_FIELDS:
        confidence = field_confidence.get(field_name)
        if confidence is not None and confidence < CONFIDENCE_THRESHOLD:
            flagged_reasons.append(
                f"{field_name} extracted with low confidence ({confidence})"
            )

    status: ValidationStatus = "flagged" if flagged_reasons else "validated"
    return ValidationResult(status=status, flagged_reasons=flagged_reasons)
