import os
from dataclasses import dataclass
from typing import Any

import anthropic
from dotenv import load_dotenv

from app.query.claude_client import DEFAULT_MODEL

load_dotenv()

EXTRACT_SUPPORT_TICKET_TOOL = {
    "name": "extract_support_ticket",
    "description": "Extract structured fields from a natural-language support ticket request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["shipping", "product_defect", "billing", "other"],
                "description": (
                    "Best-fit category for this ticket. 'other' is the correct "
                    "choice when nothing more specific clearly applies — don't "
                    "force-fit shipping/product_defect/billing."
                ),
            },
            "description": {
                "type": "string",
                "description": (
                    "A concise, factual summary of the issue, suitable to store as "
                    "the support ticket's description."
                ),
            },
            "customer_identifier": {
                "type": "string",
                "description": (
                    "The customer's name or email if mentioned in the request; "
                    "empty string if not mentioned."
                ),
            },
            "product_identifier": {
                "type": "string",
                "description": (
                    "The product name or description this ticket concerns, as close "
                    "to verbatim as possible; empty string if the ticket isn't about "
                    "a specific product (e.g. a general billing or account issue)."
                ),
            },
        },
        "required": ["category", "description", "customer_identifier", "product_identifier"],
    },
}

SYSTEM_PROMPT = """You extract structured support-ticket fields from a \
customer's natural-language message. category must be one of shipping, \
product_defect, billing, or other — pick 'other' rather than forcing a \
weak fit. customer_identifier and product_identifier should be empty \
strings, not guesses, when the message doesn't clearly name a customer or \
a specific product."""


@dataclass
class TicketExtractionResult:
    category: str
    description: str
    customer_identifier: str | None
    product_identifier: str | None
    usage: Any = None


class TicketExtractionError(Exception):
    pass


def extract_support_ticket(request_text: str) -> TicketExtractionResult:
    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        tools=[EXTRACT_SUPPORT_TICKET_TOOL],
        tool_choice={"type": "tool", "name": "extract_support_ticket"},
        messages=[{"role": "user", "content": request_text}],
    )

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise TicketExtractionError(
            f"Claude did not return an extract_support_ticket tool call "
            f"(stop_reason={response.stop_reason})"
        )

    data = tool_use.input
    try:
        return TicketExtractionResult(
            category=data["category"],
            description=data["description"],
            customer_identifier=data.get("customer_identifier") or None,
            product_identifier=data.get("product_identifier") or None,
            usage=response.usage,
        )
    except KeyError as e:
        raise TicketExtractionError(
            f"extract_support_ticket tool call missing required field: {e}"
        ) from e
