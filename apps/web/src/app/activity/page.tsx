"use client";

import { useEffect, useState } from "react";
import { listRequestLogs, type RequestLogRow } from "@/lib/api";
import { Badge } from "@/components/Badge";

type State =
  | { status: "loading" }
  | { status: "success"; rows: RequestLogRow[] }
  | { status: "error"; message: string };

export default function ActivityPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    listRequestLogs()
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
  }, []);

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
              {state.rows.map((row) => (
                <tr key={row.id} className="border-b border-black/5 dark:border-white/5">
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {new Date(row.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 pr-4">{row.request_type}</td>
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
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
