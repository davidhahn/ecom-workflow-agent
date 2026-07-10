SEARCH_POLICY_TOOL = {
    "name": "search_policy",
    "description": (
        "Search company policy documents (refund policy, shipping policy, "
        "support playbook) for relevant rules or guidance."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for in the policy documents.",
            },
        },
        "required": ["query"],
    },
}
