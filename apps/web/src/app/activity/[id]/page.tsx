"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getRequestLog, type RequestLogDetailRow } from "@/lib/api";
import { Badge } from "@/components/Badge";
import { ToolCallTrace } from "@/components/ToolCallTrace";
import { JsonPreview } from "@/components/JsonPreview";
import { useRole } from "@/lib/role-context";

type State =
  | { status: "loading" }
  | { status: "success"; detail: RequestLogDetailRow }
  | { status: "error"; message: string };

export default function ExecutionTracePage() {
  const params = useParams<{ id: string }>();
  const { role } = useRole();
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    getRequestLog(params.id, role)
      .then((detail) => {
        if (!cancelled) setState({ status: "success", detail });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({ status: "error", message: err instanceof Error ? err.message : String(err) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [params.id, role]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/activity"
          className="text-xs text-gray-500 hover:text-foreground dark:text-gray-400"
        >
          ← Back to Activity
        </Link>
        <h1 className="mt-1 text-xl font-semibold">Execution trace</h1>
      </div>

      {state.status === "loading" && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading trace…</p>
      )}

      {state.status === "error" && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {state.message}
        </div>
      )}

      {state.status === "success" && (
        <div className="flex flex-col gap-6">
          <div className="rounded-md border border-black/10 p-4 dark:border-white/10">
            <p className="text-sm font-medium">{state.detail.input}</p>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
              <span>{new Date(state.detail.created_at).toLocaleString()}</span>
              <span>{state.detail.latency_ms} ms</span>
              <span>
                {state.detail.input_tokens !== null && state.detail.output_tokens !== null
                  ? `${state.detail.input_tokens} in / ${state.detail.output_tokens} out`
                  : "no token usage"}
              </span>
              <span>
                {state.detail.estimated_cost_usd !== null
                  ? `$${state.detail.estimated_cost_usd.toFixed(4)}`
                  : "—"}
              </span>
              {state.detail.retry_count !== null && state.detail.retry_count > 0 && (
                <span>
                  {state.detail.retry_count} retr{state.detail.retry_count === 1 ? "y" : "ies"}
                </span>
              )}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge tone="neutral">{state.detail.request_type}</Badge>
              {state.detail.grounded !== null && (
                <Badge tone={state.detail.grounded ? "success" : "danger"}>
                  {state.detail.grounded ? "Grounded" : "Ungrounded claims detected"}
                </Badge>
              )}
              {state.detail.cached && <Badge tone="neutral">Cached</Badge>}
            </div>
          </div>

          <div>
            <p className="mb-2 text-sm font-medium">Tool calls</p>
            <ToolCallTrace
              toolCalls={state.detail.tool_calls ?? []}
              totalLatencyMs={state.detail.latency_ms}
            />
          </div>

          {state.detail.rag_chunks_retrieved !== null && (
            <div>
              <p className="mb-2 text-sm font-medium">Retrieved policy chunks</p>
              <JsonPreview value={state.detail.rag_chunks_retrieved} />
            </div>
          )}

          <div>
            <p className="mb-2 text-sm font-medium">Final output</p>
            <JsonPreview value={state.detail.output} />
          </div>
        </div>
      )}
    </div>
  );
}
