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


# Same hand-entered, no-live-pricing-API caveat as the Sonnet rates above.
# Added for the model comparison in DECISIONS.md - request_log's own
# estimated_cost_usd column still assumes Sonnet no matter which model
# actually ran, since it has no model field to look this up by. Use
# MODEL_PRICING directly when the actual model for a request is known.
HAIKU_INPUT_COST_PER_MILLION_TOKENS_USD = 1.00
HAIKU_OUTPUT_COST_PER_MILLION_TOKENS_USD = 5.00

MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (SONNET_INPUT_COST_PER_MILLION_TOKENS_USD, SONNET_OUTPUT_COST_PER_MILLION_TOKENS_USD),
    "claude-haiku-4-5-20251001": (HAIKU_INPUT_COST_PER_MILLION_TOKENS_USD, HAIKU_OUTPUT_COST_PER_MILLION_TOKENS_USD),
}


def estimate_cost_usd_for_model(
    model: str, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None
    input_rate, output_rate = MODEL_PRICING[model]
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
