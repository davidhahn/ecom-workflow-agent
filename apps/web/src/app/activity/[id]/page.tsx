"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getRequestLog, type RequestLogDetailRow } from "@/lib/api";
import { Badge } from "@/components/Badge";
import { ToolCallTrace } from "@/components/ToolCallTrace";
import { JsonPreview } from "@/components/JsonPreview";
import { useRole } from "@/lib/role-context";
import { SCENARIOS } from "@/lib/scenarios";
import {
  deriveConcreteStatus,
  deriveGuardrails,
  deriveLatencyBreakdown,
  deriveReliabilityOutcome,
  deriveWorkflowPhases,
  ragToolSummary,
  sqlToolSummary,
} from "@/lib/trace";

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

  const sourceScenario =
    state.status === "success" ? SCENARIOS.find((s) => s.input === state.detail.input) : undefined;

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-2">
        {sourceScenario ? (
          <Link
            href={`/scenarios#${sourceScenario.id}`}
            className="text-xs text-gray-500 hover:text-foreground dark:text-gray-400"
          >
            ← Back to &quot;{sourceScenario.name}&quot; on Scenarios
          </Link>
        ) : (
          <Link
            href="/activity"
            className="text-xs text-gray-500 hover:text-foreground dark:text-gray-400"
          >
            ← Back to the full request log
          </Link>
        )}
        <h1 className="text-2xl font-semibold">Execution trace</h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          What happened when this request ran, step by step. Steps labeled{" "}
          <span className="font-medium text-foreground">Model</span> were decided by Claude. Steps
          labeled <span className="font-medium text-foreground">Code</span> ran as fixed logic.
        </p>
      </div>

      {state.status === "loading" && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading trace…</p>
      )}

      {state.status === "error" && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {state.message}
        </div>
      )}

      {state.status === "success" && <TraceDetail detail={state.detail} />}
    </div>
  );
}

function TraceDetail({ detail }: { detail: RequestLogDetailRow }) {
  const phases = deriveWorkflowPhases(detail);
  const guardrails = deriveGuardrails(detail);
  const reliability = deriveReliabilityOutcome(detail);
  const concreteStatus = deriveConcreteStatus(detail);
  const latency = deriveLatencyBreakdown(detail);
  const toolCalls = detail.tool_calls ?? [];
  // The headline badge should reflect the worst thing that happened, not
  // just the reliability axis. A request can succeed with no retries while
  // a guardrail below flags a real problem, like an ungrounded claim, and
  // that shouldn't render as a clean green badge.
  const statusTone = guardrails.some((g) => g.tone === "danger")
    ? "danger"
    : guardrails.some((g) => g.tone === "warning")
      ? "warning"
      : reliability.tone;

  return (
    <div className="flex flex-col gap-8">
      {detail.cached && (
        <div className="max-w-prose rounded-md border-2 border-amber-400 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
          Served from cache. This trace is the original request that produced this answer. Claude and
          the tools below ran once, the first time this question was asked.
        </div>
      )}

      {/* Request summary */}
      <div className="rounded-md border border-black/10 p-6 dark:border-white/10">
        <p className="max-w-prose text-base font-medium">{detail.input}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Badge tone="neutral">{detail.request_type}</Badge>
          <Badge tone="neutral">{new Date(detail.created_at).toLocaleString()}</Badge>
          <Badge tone={statusTone}>{concreteStatus}</Badge>
          {detail.cached && <Badge tone="neutral">Cached</Badge>}
        </div>
      </div>

      {/* Workflow progress */}
      <div>
        <p className="mb-3 text-base font-medium">Workflow progress</p>
        <div className="flex flex-wrap items-center gap-2">
          {phases.map((phase, i) => (
            <span key={phase.label} className="flex items-center gap-2">
              <Badge tone={phase.state === "done" ? "success" : "neutral"}>{phase.label}</Badge>
              {i < phases.length - 1 && <span className="text-gray-400 dark:text-gray-600">→</span>}
            </span>
          ))}
        </div>
      </div>

      {/* Tool calls */}
      <div>
        <p className="mb-3 text-base font-medium">Tool calls</p>
        <ToolCallTrace toolCalls={toolCalls} totalLatencyMs={detail.latency_ms} llmLatencyMs={detail.llm_latency_ms} />

        {toolCalls.length > 0 && (
          <div className="mt-4 flex flex-col gap-3">
            {toolCalls.map((call) => {
              const sql = sqlToolSummary(call);
              const rag = ragToolSummary(call);
              if (sql) {
                return (
                  <div
                    key={call.sequence}
                    className="rounded-md border border-black/10 p-4 text-xs dark:border-white/10"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-gray-700 dark:text-gray-300">
                        #{call.sequence} run_sql_query
                      </p>
                      <Badge tone="neutral">Model proposed</Badge>
                      <Badge tone="neutral">Code enforced</Badge>
                    </div>
                    {sql.sql && (
                      <pre className="mt-1 overflow-x-auto rounded bg-black/5 p-2 font-mono dark:bg-white/5">
                        {sql.sql}
                      </pre>
                    )}
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      {sql.status && (
                        <Badge tone={sql.status === "success" ? "success" : "danger"}>{sql.status}</Badge>
                      )}
                      {sql.promptVersion && (
                        <span className="text-gray-500 dark:text-gray-400">
                          SQL prompt {sql.promptVersion}
                        </span>
                      )}
                    </div>
                    {sql.rejectionReason && (
                      <p className="mt-1 text-red-700 dark:text-red-400">{sql.rejectionReason}</p>
                    )}
                    <p className="mt-1 text-gray-500 dark:text-gray-400">
                      Claude wrote this query. The AST allowlist, cost gate, and read-only database
                      role decided whether it could run.
                    </p>
                  </div>
                );
              }
              if (rag) {
                return (
                  <div
                    key={call.sequence}
                    className="rounded-md border border-black/10 p-4 text-xs dark:border-white/10"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-gray-700 dark:text-gray-300">
                        #{call.sequence} search_policy
                      </p>
                      <Badge tone="neutral">Model proposed</Badge>
                      <Badge tone="neutral">Code enforced</Badge>
                    </div>
                    {rag.length === 0 ? (
                      <p className="mt-1 text-gray-500 dark:text-gray-400">No chunks cleared the relevance threshold.</p>
                    ) : (
                      <ul className="mt-1 list-disc pl-4">
                        {rag.map((chunk, i) => (
                          <li key={i}>
                            {chunk.sourceDoc}
                            {chunk.ruleNumber !== null ? ` (rule ${chunk.ruleNumber})` : ""}
                            {chunk.similarity !== null ? ` (similarity ${chunk.similarity.toFixed(3)})` : ""}
                          </li>
                        ))}
                      </ul>
                    )}
                    <p className="mt-1 text-gray-500 dark:text-gray-400">
                      Claude wrote the search query. A fixed similarity threshold decided which
                      chunks counted as relevant.
                    </p>
                  </div>
                );
              }
              return null;
            })}
          </div>
        )}
      </div>

      {/* Guardrail outcomes */}
      <div>
        <p className="mb-3 text-base font-medium">Guardrail outcomes</p>
        {guardrails.length === 0 ? (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            No guardrail checks apply to this request type.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {guardrails.map((field) => (
              <div key={field.label} className="flex flex-col gap-1 text-xs">
                <div className="flex flex-wrap items-baseline gap-2">
                  <Badge tone={field.tone}>{field.label}</Badge>
                  <span className="text-gray-600 dark:text-gray-400">{field.value}</span>
                </div>
                <p className="text-gray-500 dark:text-gray-500">{field.caption}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reliability and operational data */}
      <div>
        <p className="mb-3 text-base font-medium">Reliability &amp; operational data</p>
        <div className="flex flex-wrap gap-2">
          <Badge tone={reliability.tone}>{reliability.label}</Badge>
        </div>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
          <span>{latency.totalMs} ms total</span>
          {latency.llmMs !== null ? (
            <>
              <span>{latency.llmMs} ms in Claude API calls</span>
              <span>{latency.toolMs} ms in tools</span>
              <span>{latency.otherMs} ms other (network, logging)</span>
            </>
          ) : (
            toolCalls.length > 0 && <span>{latency.toolMs} ms in tools</span>
          )}
          <span>
            {detail.input_tokens !== null && detail.output_tokens !== null
              ? `${detail.input_tokens} input tokens / ${detail.output_tokens} output tokens`
              : "no token usage"}
          </span>
          <span>
            {detail.estimated_cost_usd !== null ? `$${detail.estimated_cost_usd.toFixed(4)}` : "—"}
          </span>
          <span>{detail.cached ? "cached" : "not cached"}</span>
          {detail.retry_count !== null && (
            <span>
              {detail.retry_count} retr{detail.retry_count === 1 ? "y" : "ies"}
            </span>
          )}
        </div>
      </div>

      <details className="rounded-md border border-black/10 dark:border-white/10">
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium">
          Raw request log data
        </summary>
        <div className="flex flex-col gap-4 border-t border-black/10 px-4 py-3 dark:border-white/10">
          {detail.rag_chunks_retrieved !== null && (
            <div>
              <p className="mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
                Retrieved policy chunks
              </p>
              <JsonPreview value={detail.rag_chunks_retrieved} />
            </div>
          )}
          <div>
            <p className="mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
              Final output
            </p>
            <JsonPreview value={detail.output} />
          </div>
        </div>
      </details>
    </div>
  );
}
