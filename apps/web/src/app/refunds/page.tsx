"use client";

import { useState } from "react";
import {
  evaluateRefund,
  formatRetryAfter,
  RateLimitedError,
  type RefundEvaluateResponse,
  type RateLimitInfo,
} from "@/lib/api";
import { Badge, type BadgeTone } from "@/components/Badge";
import { useRole } from "@/lib/role-context";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: RefundEvaluateResponse }
  | { status: "error"; message: string };

const STATUS_TONE: Record<string, BadgeTone> = {
  approved: "success",
  denied: "danger",
  requires_manager_approval: "warning",
  flagged_for_review: "warning",
  could_not_process: "neutral",
};

export default function RefundsPage() {
  const [requestText, setRequestText] = useState("");
  const [state, setState] = useState<State>({ status: "idle" });
  const [rateLimit, setRateLimit] = useState<RateLimitInfo | null>(null);
  const { role } = useRole();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!requestText.trim() || state.status === "loading") return;
    setState({ status: "loading" });
    try {
      const { data, rateLimit: rl } = await evaluateRefund(requestText, role);
      setState({ status: "success", result: data });
      setRateLimit(rl);
    } catch (err) {
      if (err instanceof RateLimitedError) {
        setState({ status: "error", message: formatRetryAfter(err.retryAfterSeconds) });
      } else {
        setState({ status: "error", message: err instanceof Error ? err.message : String(err) });
      }
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Refund evaluator</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Paste a natural-language refund request. This evaluates a decision only — it never
          writes to the refunds table.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <textarea
          value={requestText}
          onChange={(e) => setRequestText(e.target.value)}
          placeholder="e.g. I'd like to return the wireless headphones I bought, they arrived defective."
          rows={3}
          className="w-full rounded-md border border-black/15 bg-transparent p-3 text-sm outline-none focus:border-black/40 dark:border-white/15 dark:focus:border-white/40"
        />
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={state.status === "loading" || !requestText.trim()}
            className="self-start rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
          >
            {state.status === "loading" ? "Evaluating…" : "Evaluate"}
          </button>
          {rateLimit?.remaining !== null && rateLimit?.remaining !== undefined && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {rateLimit.remaining} of {rateLimit.limit} requests remaining this hour
            </span>
          )}
        </div>
      </form>

      {state.status === "error" && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {state.message}
        </div>
      )}

      {state.status === "success" && (
        <div className="flex flex-col gap-4 rounded-md border border-black/10 p-4 dark:border-white/10">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={STATUS_TONE[state.result.status] ?? "neutral"}>
              {state.result.status}
            </Badge>
            {state.result.rule_applied !== null && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                rule {state.result.rule_applied}
              </span>
            )}
          </div>

          <p className="text-sm">{state.result.reasoning}</p>

          {Object.keys(state.result.extracted_fields).length > 0 && (
            <div className="text-xs text-gray-500 dark:text-gray-400">
              <p className="font-medium text-gray-700 dark:text-gray-300">Extracted fields</p>
              <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
                {Object.entries(state.result.extracted_fields).map(([key, value]) => (
                  <div key={key} className="contents">
                    <dt className="font-mono">{key}</dt>
                    <dd>{value === null || value === undefined ? "—" : String(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
