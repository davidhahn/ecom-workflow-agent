GET_SHIPMENT_STATUS_TOOL = {
    "name": "get_shipment_status",
    "description": (
        "Look up shipment records by product, status, and/or expected delivery "
        "date range. Read-only. Use this for shipment/delivery questions instead "
        "of run_sql_query — shipments is not one of run_sql_query's allowed tables."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "product_name": {
                "type": "string",
                "description": (
                    "Filter to shipments whose order contains this product "
                    "(partial match). Optional."
                ),
            },
            "status": {
                "type": "string",
                "enum": ["pending", "shipped", "delivered", "delayed"],
                "description": "Filter by shipment status. Optional.",
            },
            "expected_delivery_before": {
                "type": "string",
                "description": (
                    "ISO 8601 date/datetime — only shipments expected on or "
                    "before this date. Optional."
                ),
            },
            "expected_delivery_after": {
                "type": "string",
                "description": (
                    "ISO 8601 date/datetime — only shipments expected on or "
                    "after this date. Optional."
                ),
            },
        },
        "required": [],
    },
}
