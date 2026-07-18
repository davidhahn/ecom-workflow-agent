DRAFT_SUPPORT_TICKET_TOOL = {
    "name": "draft_support_ticket",
    "description": (
        "Draft a support ticket from a natural-language request. Writes nothing "
        "to the database — returns a draft_id that must be passed to "
        "confirm_support_ticket before the ticket is actually created."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "request_text": {
                "type": "string",
                "description": "The customer's free-text support request.",
            },
        },
        "required": ["request_text"],
    },
}

CONFIRM_SUPPORT_TICKET_TOOL = {
    "name": "confirm_support_ticket",
    "description": (
        "Confirm a previously drafted support ticket, writing it to the database "
        "for real. Requires a draft_id from a prior draft_support_ticket call."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "draft_id": {
                "type": "string",
                "description": "The draft_id returned by draft_support_ticket.",
            },
        },
        "required": ["draft_id"],
    },
}
