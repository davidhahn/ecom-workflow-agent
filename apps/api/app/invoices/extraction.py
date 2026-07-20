import os
from dataclasses import dataclass
from datetime import date
from typing import Any

import anthropic
from dotenv import load_dotenv

from app.query.claude_client import DEFAULT_MODEL

load_dotenv()

CONFIDENCE_FIELDS = (
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "subtotal_cents",
    "tax_cents",
    "total_cents",
)

EXTRACT_VENDOR_INVOICE_TOOL = {
    "name": "extract_vendor_invoice",
    "description": (
        "Extract structured fields from an image of a vendor invoice, with a "
        "self-reported confidence score (0-1) for each extracted field."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "vendor_name": {
                "type": "string",
                "description": "The vendor/company name on the invoice.",
            },
            "invoice_number": {
                "type": "string",
                "description": "The invoice number as printed on the invoice.",
            },
            "invoice_date": {
                "type": "string",
                "description": "The invoice date, in YYYY-MM-DD format.",
            },
            "subtotal_cents": {
                "type": "integer",
                "description": "Subtotal amount in cents, before tax.",
            },
            "tax_cents": {
                "type": "integer",
                "description": "Tax amount in cents.",
            },
            "total_cents": {
                "type": "integer",
                "description": "Total amount in cents, including tax.",
            },
            "line_items": {
                "type": "array",
                "description": "Line items listed on the invoice.",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price_cents": {"type": "integer"},
                        "amount_cents": {"type": "integer"},
                    },
                    "required": ["description", "amount_cents"],
                },
            },
            "field_confidence": {
                "type": "object",
                "description": (
                    "Self-reported extraction confidence (0-1) for each of: "
                    + ", ".join(CONFIDENCE_FIELDS)
                ),
                "properties": {name: {"type": "number"} for name in CONFIDENCE_FIELDS},
                "required": list(CONFIDENCE_FIELDS),
            },
        },
        "required": [
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "line_items",
            "field_confidence",
        ],
    },
}

SYSTEM_PROMPT = """You extract structured vendor-invoice fields from an image \
of an invoice. Report amounts in integer cents, not dollars. invoice_date \
must be in YYYY-MM-DD format. For field_confidence, report your genuine \
extraction confidence (0-1) for each field — low confidence for anything \
blurry, ambiguous, or partially obscured in the image, not a default high \
score."""


@dataclass
class InvoiceExtractionResult:
    vendor_name: str
    invoice_number: str
    invoice_date: date
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    line_items: list[dict[str, Any]]
    field_confidence: dict[str, float]
    usage: Any = None


class InvoiceExtractionError(Exception):
    pass


def extract_vendor_invoice(image_base64: str, media_type: str) -> InvoiceExtractionResult:
    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[EXTRACT_VENDOR_INVOICE_TOOL],
        tool_choice={"type": "tool", "name": "extract_vendor_invoice"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": "Extract the invoice fields from this image."},
                ],
            }
        ],
    )

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise InvoiceExtractionError(
            f"Claude did not return an extract_vendor_invoice tool call "
            f"(stop_reason={response.stop_reason})"
        )

    data = tool_use.input
    try:
        return InvoiceExtractionResult(
            vendor_name=data["vendor_name"],
            invoice_number=data["invoice_number"],
            invoice_date=date.fromisoformat(data["invoice_date"]),
            subtotal_cents=data["subtotal_cents"],
            tax_cents=data["tax_cents"],
            total_cents=data["total_cents"],
            line_items=data.get("line_items") or [],
            field_confidence={name: data["field_confidence"][name] for name in CONFIDENCE_FIELDS},
            usage=response.usage,
        )
    except (KeyError, ValueError) as e:
        raise InvoiceExtractionError(
            f"extract_vendor_invoice tool call missing or invalid required field: {e}"
        ) from e
