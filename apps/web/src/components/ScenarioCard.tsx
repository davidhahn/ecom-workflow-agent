"use client";

import Link from "next/link";
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
import { SnapshotCalculationWarning } from "@/components/SnapshotCalculationWarning";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import type { Scenario } from "@/lib/scenarios";
import { useRole } from "@/lib/role-context";
import { getScenarioSnapshot, SNAPSHOT_CAPTURED_AT } from "@/lib/snapshots";

type State =
  | { status: "snapshot" }
  | { status: "loading" }
  | { status: "success"; endpoint: "analyze"; result: AnalyzeResponse }
  | { status: "success"; endpoint: "refund"; result: RefundEvaluateResponse }
  | { status: "error"; message: string };

const CAPTURED_DATE = new Date(SNAPSHOT_CAPTURED_AT).toLocaleDateString(undefined, {
  year: "numeric",
  month: "long",
  day: "numeric",
});

const EVIDENCE_LINKS: Record<string, { href: string; label: string; note: string }> = {
  "data-analysis": {
    href: "/evaluation-lab#findings-finding-2-sql-calculation-errors",
    label: "How I checked the calculations",
    note: "Independent result checks exposed errors that SQL safety checks missed. The saved experiments cover the direct SQL path, not every Ask response.",
  },
  "policy-retrieval": {
    href: "/evaluation-lab#findings-finding-5-differences-in-the-deployed-environment",
    label: "What changed in production retrieval",
    note: "Embedding-provider differences exposed a ranking failure. This captured result does not establish that every live policy question succeeds.",
  },
};

export function ScenarioCard({ scenario, traceNewTab = false }: { scenario: Scenario; traceNewTab?: boolean }) {
  const [state, setState] = useState<State>({ status: "snapshot" });
  const { role } = useRole();
  const snapshot = getScenarioSnapshot(scenario);
  const evidence = EVIDENCE_LINKS[scenario.id] ?? {
    href: "/architecture#refund-requests",
    label: "How refund decisions are enforced",
    note: "Code applies the policy rules after extraction and order resolution. Isolated rule tests do not validate the full language-to-decision path.",
  };

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
    <Card id={scenario.id} className="scroll-mt-20 gap-8 py-8">
      <CardHeader className="gap-2">
        <h2 className="text-lg leading-snug font-semibold">{scenario.name}</h2>
        <CardDescription className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          {scenario.businessContext}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-col gap-8">
        {/* A result is always on screen now, either the captured snapshot or
            a fresh run, so the promise is always right there to compare
            against. */}
        <details
          open={state.status === "snapshot" || state.status === "success" || undefined}
          className="rounded-md bg-black/[0.02] dark:bg-white/[0.03]"
        >
          <summary className="cursor-pointer select-none px-4 py-3 text-xs font-medium text-gray-700 dark:text-gray-300">
            Expected behavior
          </summary>
          <p className="max-w-prose px-4 pb-3 text-sm text-gray-500 dark:text-gray-400">
            {scenario.expectedBehavior}
          </p>
        </details>

        <div className="rounded-md border border-black/10 p-4 dark:border-white/10">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Request sent to the agent
          </p>
          <blockquote className="mt-2 max-w-prose text-sm whitespace-pre-wrap wrap-anywhere text-gray-700 dark:text-gray-300">
            {scenario.input}
          </blockquote>
        </div>

        <Button type="button" onClick={run} disabled={state.status === "loading"} className="self-start">
          {state.status === "loading" ? "Running…" : "Run it fresh"}
        </Button>

        {state.status === "error" && (
          <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            {state.message}
          </div>
        )}

        {state.status === "snapshot" && (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Captured from a real run on {CAPTURED_DATE}.
            </p>
            {scenario.id === "data-analysis" && <SnapshotCalculationWarning />}
            {scenario.endpoint === "analyze" ? (
              <AnalyzeResult result={snapshot as AnalyzeResponse} traceHref={null} />
            ) : (
              <RefundResult result={snapshot as RefundEvaluateResponse} traceHref={null} />
            )}
          </div>
        )}

        {state.status === "success" && state.endpoint === "analyze" && (
          <AnalyzeResult result={state.result} traceNewTab={traceNewTab} />
        )}
        {state.status === "success" && state.endpoint === "refund" && <RefundResult result={state.result} traceNewTab={traceNewTab} />}

        <div className="border-t border-black/10 pt-4 dark:border-white/10">
          {state.status === "snapshot" && (
            <p className="mb-3 text-sm text-gray-500 dark:text-gray-400">
              This is a saved result. Run it fresh to inspect a new execution trace.
            </p>
          )}
          <Link href={evidence.href} className="text-sm font-medium text-accent underline underline-offset-2 hover:no-underline">
            {evidence.label} →
          </Link>
          <p className="mt-2 max-w-prose text-sm text-gray-500 dark:text-gray-400">{evidence.note}</p>
        </div>
      </CardContent>
    </Card>
  );
}
