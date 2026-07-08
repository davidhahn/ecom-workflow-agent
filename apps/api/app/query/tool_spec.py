RUN_SQL_QUERY_TOOL = {
    "name": "run_sql_query",
    "description": "Execute a read-only SQL query against the ops database to answer analytical questions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "A single SELECT statement. Available tables: customers "
                    "(no email column visible), products, orders, order_items, "
                    "refunds, support_tickets."
                ),
            },
            "intent": {
                "type": "string",
                "description": "One sentence: what business question does this query answer?",
            },
        },
        "required": ["query", "intent"],
    },
}
