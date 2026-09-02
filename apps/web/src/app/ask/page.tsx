"use client";

import { useState } from "react";
import {
  analyzeQuestion,
  formatRetryAfter,
  RateLimitedError,
  type AnalyzeResponse,
  type RateLimitInfo,
} from "@/lib/api";
import { AnalyzeResult } from "@/components/AnalyzeResult";
import { ExampleChip } from "@/components/ExampleChip";
import { NextSteps } from "@/components/NextSteps";
import { Button } from "@/components/ui/button";
import { useRole } from "@/lib/role-context";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: AnalyzeResponse }
  | { status: "error"; message: string };

const EXAMPLE_QUESTIONS = [
  "Which products have the highest refund rate?",
  "What does our policy require before a damaged-shipping refund can be processed?",
  "We've had a lot of refund requests for the Bluetooth Headphones Pro, what's driving that, and does it violate our policy?",
  "Are any shipments delayed right now?",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<State>({ status: "idle" });
  const [rateLimit, setRateLimit] = useState<RateLimitInfo | null>(null);
  const { role } = useRole();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || state.status === "loading") return;
    setState({ status: "loading" });
    try {
      const { data, rateLimit: rl } = await analyzeQuestion(question, role);
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
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold">Ask</h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          Test the agent across data and knowledge. Claude decides whether the question needs a
          SQL query, a policy lookup, or both. Deterministic controls decide what data it&apos;s
          allowed to reach. A grounding check flags any claim the retrieved evidence doesn&apos;t
          support.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What is the refund rate for Electronics this quarter?"
          rows={3}
          className="w-full rounded-md border border-black/15 bg-transparent p-4 text-sm outline-none focus:border-black/40 dark:border-white/15 dark:focus:border-white/40"
        />
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={state.status === "loading" || !question.trim()} className="self-start">
            {state.status === "loading" ? "Asking…" : "Ask"}
          </Button>
          {rateLimit?.remaining !== null && rateLimit?.remaining !== undefined && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {rateLimit.remaining} of {rateLimit.limit} requests remaining this hour
            </span>
          )}
        </div>
      </form>

      <div className="flex flex-col gap-2">
        <p className="text-sm text-gray-500 dark:text-gray-400">Not sure what to ask? Try one of these.</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((example) => (
            <ExampleChip key={example} label={example} onClick={() => setQuestion(example)} />
          ))}
        </div>
      </div>

      {state.status === "error" && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {state.message}
        </div>
      )}

      {state.status === "success" && <AnalyzeResult result={state.result} />}

      <NextSteps
        links={[
          {
            href: "/activity",
            label: "System Traces",
            note: "See every request logged, including this one.",
          },
          {
            href: "/evaluation-lab",
            label: "Evaluation Lab",
            note: "Check the real numbers behind this kind of answer.",
          },
        ]}
      />
    </div>
  );
}
