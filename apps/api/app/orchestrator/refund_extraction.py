import os
from dataclasses import dataclass
from typing import Any

import anthropic
from dotenv import load_dotenv

from app.query.claude_client import DEFAULT_MODEL

load_dotenv()

EXTRACT_REFUND_REQUEST_TOOL = {
    "name": "extract_refund_request",
    "description": "Extract structured fields from a natural-language refund request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "product_identifier": {
                "type": "string",
                "description": (
                    "The product name or description the customer refers to, as "
                    "close to verbatim as possible."
                ),
            },
            "customer_identifier": {
                "type": "string",
                "description": (
                    "The customer's name or email if mentioned in the request; "
                    "empty string if not mentioned."
                ),
            },
            "reason_confident": {
                "type": "boolean",
                "description": (
                    "True only if the request text clearly and unambiguously maps "
                    "to exactly one of the four reason codes. False if the text is "
                    "vague, mixed, or doesn't map cleanly to any of them — do not "
                    "guess in that case."
                ),
            },
            "reason": {
                "type": "string",
                "enum": ["defective", "wrong_item", "changed_mind", "damaged_shipping"],
                "description": (
                    "Best-guess reason code. Only meaningful when reason_confident "
                    "is true."
                ),
            },
            "evidence_submitted": {
                "type": "boolean",
                "description": (
                    "Whether the customer states or implies they have already "
                    "provided photo evidence. Only relevant when reason is "
                    "damaged_shipping; false otherwise."
                ),
            },
        },
        "required": [
            "product_identifier",
            "customer_identifier",
            "reason_confident",
            "reason",
            "evidence_submitted",
        ],
    },
}

SYSTEM_PROMPT = """You extract structured refund-request fields from a \
customer's natural-language message. Only the four reason codes defective, \
wrong_item, changed_mind, and damaged_shipping are valid. If the message \
doesn't clearly and unambiguously map to exactly one of them, set \
reason_confident to false rather than guessing — a low-confidence guess is \
worse than an honest "can't tell"."""


@dataclass
class ExtractionResult:
    product_identifier: str
    customer_identifier: str | None
    reason_confident: bool
    reason: str
    evidence_submitted: bool
    usage: Any = None


class ExtractionError(Exception):
    pass


def extract_refund_request(request_text: str) -> ExtractionResult:
    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        tools=[EXTRACT_REFUND_REQUEST_TOOL],
        tool_choice={"type": "tool", "name": "extract_refund_request"},
        messages=[{"role": "user", "content": request_text}],
    )

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise ExtractionError(
            f"Claude did not return an extract_refund_request tool call "
            f"(stop_reason={response.stop_reason})"
        )

    data = tool_use.input
    try:
        return ExtractionResult(
            product_identifier=data["product_identifier"],
            customer_identifier=data.get("customer_identifier") or None,
            reason_confident=data["reason_confident"],
            reason=data["reason"],
            evidence_submitted=data["evidence_submitted"],
            usage=response.usage,
        )
    except KeyError as e:
        raise ExtractionError(
            f"extract_refund_request tool call missing required field: {e}"
        ) from e
