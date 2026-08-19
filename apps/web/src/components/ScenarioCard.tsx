"use client";

import { useState } from "react";
import {
  analyzeQuestion,
  evaluateRefund,
  formatRetryAfter,
  RateLimitedError,
  type AnalyzeResponse,
  type RefundEvaluateResponse,
} from "@/lib/api";
import { AnalyzeResult } from "@/components/AnalyzeResult";
import { RefundResult } from "@/components/RefundResult";
import type { Scenario } from "@/lib/scenarios";
import { useRole } from "@/lib/role-context";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; endpoint: "analyze"; result: AnalyzeResponse }
  | { status: "success"; endpoint: "refund"; result: RefundEvaluateResponse }
  | { status: "error"; message: string };

export function ScenarioCard({ scenario }: { scenario: Scenario }) {
  const [state, setState] = useState<State>({ status: "idle" });
  const { role } = useRole();

  async function run() {
    if (state.status === "loading") return;
    setState({ status: "loading" });
    try {
      if (scenario.endpoint === "analyze") {
        const { data } = await analyzeQuestion(scenario.input, role);
        setState({ status: "success", endpoint: "analyze", result: data });
      } else {
        const { data } = await evaluateRefund(scenario.input, role);
        setState({ status: "success", endpoint: "refund", result: data });
      }
    } catch (err) {
      if (err instanceof RateLimitedError) {
        setState({ status: "error", message: formatRetryAfter(err.retryAfterSeconds) });
      } else {
        setState({ status: "error", message: err instanceof Error ? err.message : String(err) });
      }
    }
  }

  return (
    <div
      id={scenario.id}
      className="flex flex-col gap-4 rounded-md border border-black/10 p-4 scroll-mt-20 dark:border-white/10"
    >
      <div>
        <h2 className="text-base font-semibold">{scenario.name}</h2>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{scenario.businessContext}</p>
      </div>

      <div className="rounded-md border border-dashed border-black/15 p-3 text-xs dark:border-white/15">
        <p className="font-medium text-gray-700 dark:text-gray-300">Expected behavior</p>
        <p className="mt-1 text-gray-500 dark:text-gray-400">{scenario.expectedBehavior}</p>
      </div>

      <button
        type="button"
        onClick={run}
        disabled={state.status === "loading"}
        className="self-start rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
      >
        {state.status === "loading" ? "Running…" : "Run scenario"}
      </button>

      {state.status === "error" && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {state.message}
        </div>
      )}

      {state.status === "success" && state.endpoint === "analyze" && (
        <AnalyzeResult result={state.result} />
      )}
      {state.status === "success" && state.endpoint === "refund" && <RefundResult result={state.result} />}
    </div>
  );
}
