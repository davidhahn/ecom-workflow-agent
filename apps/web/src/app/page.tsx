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

export default function ScenarioDemoPage() {
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
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold">Scenario demo</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Five curated requests exercise the agent&apos;s SQL and policy-retrieval tool paths and its
          deterministic refund gate, including how it refuses and how it holds up against
          adversarial input. Run any of them to see the actual result and the execution trace
          behind it.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {SCENARIOS.map((scenario) => (
          <ScenarioCard key={scenario.id} scenario={scenario} />
        ))}
      </div>

      <div className="flex flex-col gap-3 border-t border-black/10 pt-6 dark:border-white/10">
        <div>
          <h2 className="text-base font-semibold">Try your own refund request</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Same refund evaluator as above, free-form. Evaluates a decision only — it never writes
            to the refunds table.
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

        {state.status === "success" && <RefundResult result={state.result} />}
      </div>
    </div>
  );
}
