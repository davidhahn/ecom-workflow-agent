DRAFT_VENDOR_INVOICE_TOOL = {
    "name": "draft_vendor_invoice",
    "description": (
        "Draft a vendor invoice from an image via structured extraction, then run "
        "deterministic validation (arithmetic consistency, duplicate check, date "
        "sanity, per-field confidence) against the extracted draft. Writes nothing "
        "to the database — returns a draft_id that must be passed to "
        "confirm_vendor_invoice before the invoice is actually created."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "image_base64": {
                "type": "string",
                "description": "Base64-encoded invoice image.",
            },
            "media_type": {
                "type": "string",
                "enum": ["image/jpeg", "image/png"],
                "description": "MIME type of the invoice image.",
            },
        },
        "required": ["image_base64", "media_type"],
    },
}

CONFIRM_VENDOR_INVOICE_TOOL = {
    "name": "confirm_vendor_invoice",
    "description": (
        "Confirm a previously drafted vendor invoice, writing it to the database "
        "for real — including invoices flagged for review, since flagging means "
        "'needs human review', not 'reject and discard'. Re-checks for a duplicate "
        "(vendor_name, invoice_number) pair at confirm-time, not just draft-time. "
        "Requires a draft_id from a prior draft_vendor_invoice call."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "draft_id": {
                "type": "string",
                "description": "The draft_id returned by draft_vendor_invoice.",
            },
        },
        "required": ["draft_id"],
    },
}
