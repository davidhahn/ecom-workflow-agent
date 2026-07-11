# Hardcoded per-token pricing for the pinned model (claude-sonnet-4-6 — see
# app/query/claude_client.py's DEFAULT_MODEL / ARCHITECTURE.md's
# Orchestration row). There is no live pricing API to read from; these are
# manually-entered rates and MUST be updated by hand if the pinned model
# ever changes, or every cost estimate silently becomes wrong for the new
# model without any error to signal it.
SONNET_INPUT_COST_PER_MILLION_TOKENS_USD = 3.00
SONNET_OUTPUT_COST_PER_MILLION_TOKENS_USD = 15.00


def estimate_cost_usd(input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None
    return (
        input_tokens * SONNET_INPUT_COST_PER_MILLION_TOKENS_USD
        + output_tokens * SONNET_OUTPUT_COST_PER_MILLION_TOKENS_USD
    ) / 1_000_000
