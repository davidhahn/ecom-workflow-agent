"use client";

import { Fragment, useEffect, useState } from "react";
import { getRequestLog, listRequestLogs, type RequestLogDetailRow, type RequestLogRow } from "@/lib/api";
import { Badge } from "@/components/Badge";
import { ToolCallTrace } from "@/components/ToolCallTrace";
import { useRole } from "@/lib/role-context";

type State =
  | { status: "loading" }
  | { status: "success"; rows: RequestLogRow[] }
  | { status: "error"; message: string };

// Per-row detail cache for the expandable trace view, keyed by request id.
// "loading"/"error" are transient states before the real row lands; only
// request_type 'analyze' rows are ever fetched into this — see toggleExpand.
type DetailState = RequestLogDetailRow | "loading" | "error";

export default function ActivityPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, DetailState>>({});
  const { role } = useRole();

  useEffect(() => {
    let cancelled = false;
    listRequestLogs(role)
      .then((rows) => {
        if (!cancelled) setState({ status: "success", rows });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({ status: "error", message: err instanceof Error ? err.message : String(err) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [role]);

  function toggleExpand(row: RequestLogRow) {
    if (row.request_type !== "analyze") return;

    if (expandedId === row.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(row.id);

    if (!details[row.id]) {
      setDetails((prev) => ({ ...prev, [row.id]: "loading" }));
      getRequestLog(row.id, role)
        .then((detail) => setDetails((prev) => ({ ...prev, [row.id]: detail })))
        .catch(() => setDetails((prev) => ({ ...prev, [row.id]: "error" })));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Activity</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Most recent requests across all endpoints.
        </p>
      </div>

      {state.status === "loading" && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>
      )}

      {state.status === "error" && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {state.message}
        </div>
      )}

      {state.status === "success" && state.rows.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No requests logged yet.</p>
      )}

      {state.status === "success" && state.rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-black/10 text-xs text-gray-500 dark:border-white/10 dark:text-gray-400">
                <th className="py-2 pr-4 font-medium">Time</th>
                <th className="py-2 pr-4 font-medium">Type</th>
                <th className="py-2 pr-4 font-medium">Latency</th>
                <th className="py-2 pr-4 font-medium">Tokens</th>
                <th className="py-2 pr-4 font-medium">Cost</th>
                <th className="py-2 pr-4 font-medium">Grounded</th>
                <th className="py-2 pr-4 font-medium">Cached</th>
              </tr>
            </thead>
            <tbody>
              {state.rows.map((row) => {
                const isAnalyze = row.request_type === "analyze";
                const isExpanded = isAnalyze && expandedId === row.id;
                const detail = details[row.id];

                return (
                  <Fragment key={row.id}>
                    <tr
                      onClick={() => toggleExpand(row)}
                      className={`border-b border-black/5 dark:border-white/5 ${
                        isAnalyze ? "cursor-pointer hover:bg-black/[0.03] dark:hover:bg-white/[0.03]" : ""
                      }`}
                    >
                      <td className="py-2 pr-4 whitespace-nowrap">
                        {new Date(row.created_at).toLocaleString()}
                      </td>
                      <td className="py-2 pr-4">
                        {isAnalyze && (
                          <span className="mr-1 inline-block w-3 text-gray-400">
                            {isExpanded ? "▾" : "▸"}
                          </span>
                        )}
                        {row.request_type}
                      </td>
                      <td className="py-2 pr-4">{row.latency_ms} ms</td>
                      <td className="py-2 pr-4">
                        {row.input_tokens !== null && row.output_tokens !== null
                          ? `${row.input_tokens} in / ${row.output_tokens} out`
                          : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        {row.estimated_cost_usd !== null
                          ? `$${row.estimated_cost_usd.toFixed(4)}`
                          : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        {row.grounded === null ? (
                          "—"
                        ) : (
                          <Badge tone={row.grounded ? "success" : "danger"}>
                            {row.grounded ? "yes" : "no"}
                          </Badge>
                        )}
                      </td>
                      <td className="py-2 pr-4">
                        {row.cached && <Badge tone="neutral">cached</Badge>}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="border-b border-black/5 dark:border-white/5">
                        <td colSpan={7} className="bg-black/[0.02] px-4 py-3 dark:bg-white/[0.02]">
                          {detail === "loading" && (
                            <p className="text-xs text-gray-500 dark:text-gray-400">Loading trace…</p>
                          )}
                          {detail === "error" && (
                            <p className="text-xs text-red-600 dark:text-red-400">Failed to load trace.</p>
                          )}
                          {detail && detail !== "loading" && detail !== "error" && (
                            <ToolCallTrace
                              toolCalls={detail.tool_calls ?? []}
                              totalLatencyMs={row.latency_ms}
                            />
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
