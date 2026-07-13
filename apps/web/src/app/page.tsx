"use client";

import { useState } from "react";
import { analyzeQuestion, type AnalyzeResponse } from "@/lib/api";
import { Badge } from "@/components/Badge";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: AnalyzeResponse }
  | { status: "error"; message: string };

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<State>({ status: "idle" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || state.status === "loading") return;
    setState({ status: "loading" });
    try {
      const result = await analyzeQuestion(question);
      setState({ status: "success", result });
    } catch (err) {
      setState({ status: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Ask</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Ask a question over ops data (SQL) and/or refund policy (RAG). The agent decides which
          tools it needs.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What is the refund rate for Electronics this quarter?"
          rows={3}
          className="w-full rounded-md border border-black/15 bg-transparent p-3 text-sm outline-none focus:border-black/40 dark:border-white/15 dark:focus:border-white/40"
        />
        <button
          type="submit"
          disabled={state.status === "loading" || !question.trim()}
          className="self-start rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
        >
          {state.status === "loading" ? "Asking…" : "Ask"}
        </button>
      </form>

      {state.status === "error" && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {state.message}
        </div>
      )}

      {state.status === "success" && (
        <div className="flex flex-col gap-4 rounded-md border border-black/10 p-4 dark:border-white/10">
          <div className="flex flex-wrap gap-2">
            <Badge tone={state.result.sql_used ? "success" : "neutral"}>
              {state.result.sql_used ? "SQL used" : "SQL not used"}
            </Badge>
            <Badge tone={state.result.rag_used ? "success" : "neutral"}>
              {state.result.rag_used ? "Policy lookup used" : "Policy lookup not used"}
            </Badge>
            <Badge tone={state.result.grounded ? "success" : "danger"}>
              {state.result.grounded ? "Grounded" : "Ungrounded claims detected"}
            </Badge>
          </div>

          <p className="whitespace-pre-wrap text-sm">{state.result.answer}</p>

          {state.result.ungrounded_claims.length > 0 && (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
              <p className="font-medium">Ungrounded claims:</p>
              <ul className="mt-1 list-disc pl-4">
                {state.result.ungrounded_claims.map((claim) => (
                  <li key={claim}>{claim}</li>
                ))}
              </ul>
            </div>
          )}

          {state.result.sources.length > 0 && (
            <div className="text-xs text-gray-500 dark:text-gray-400">
              <p className="font-medium text-gray-700 dark:text-gray-300">Sources</p>
              <ul className="mt-1 list-disc pl-4">
                {state.result.sources.map((source, i) => (
                  <li key={i}>
                    {source.source_doc}
                    {source.rule_number !== null ? ` — rule ${source.rule_number}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
