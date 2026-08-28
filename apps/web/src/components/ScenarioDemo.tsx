"use client";

import { useState } from "react";
import {
  evaluateRefund,
  formatRetryAfter,
  RateLimitedError,
  type RateLimitInfo,
  type RefundEvaluateResponse,
} from "@/lib/api";
import { RefundResult } from "@/components/RefundResult";
import { ScenarioCard } from "@/components/ScenarioCard";
import { SCENARIOS } from "@/lib/scenarios";
import { useRole } from "@/lib/role-context";

type FreeformState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: RefundEvaluateResponse }
  | { status: "error"; message: string };

export function ScenarioDemo() {
  const [requestText, setRequestText] = useState("");
  const [state, setState] = useState<FreeformState>({ status: "idle" });
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
    <div className="flex flex-col gap-12">
      <div className="flex flex-col gap-6">
        {SCENARIOS.map((scenario) => (
          <ScenarioCard key={scenario.id} scenario={scenario} />
        ))}
      </div>

      <details className="border-t border-black/10 pt-10 dark:border-white/10">
        <summary className="cursor-pointer select-none">
          <h2 className="inline text-lg font-semibold">Try your own refund request</h2>
          <span className="mt-1 block max-w-prose text-sm text-gray-500 dark:text-gray-400">
            Same refund evaluator as above, free-form. It evaluates a decision and writes nothing
            to the refunds table.
          </span>
        </summary>

        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
          <textarea
            value={requestText}
            onChange={(e) => setRequestText(e.target.value)}
            placeholder="e.g. I'd like to return the wireless headphones I bought, they arrived defective."
            rows={3}
            className="w-full rounded-md border border-black/15 bg-transparent p-4 text-sm outline-none focus:border-black/40 dark:border-white/15 dark:focus:border-white/40"
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
          <div className="mt-3 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            {state.message}
          </div>
        )}

        {state.status === "success" && (
          <div className="mt-3">
            <RefundResult result={state.result} />
          </div>
        )}
      </details>
    </div>
  );
}
