"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listRequestLogs, type RequestLogRow } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { NextSteps } from "@/components/NextSteps";
import { useRole } from "@/lib/role-context";

type State =
  | { status: "loading" }
  | { status: "success"; rows: RequestLogRow[] }
  | { status: "error"; message: string };

export default function ActivityPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const { role } = useRole();
  const router = useRouter();

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

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold">Activity</h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          Most recent requests across all endpoints. Any row opens that request&apos;s execution
          trace.
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
                <th className="py-3 pr-4 font-medium tracking-wide uppercase">Time</th>
                <th className="py-3 pr-4 font-medium tracking-wide uppercase">Type</th>
                <th className="py-3 pr-4 font-medium tracking-wide uppercase">Latency</th>
                <th className="py-3 pr-4 font-medium tracking-wide uppercase">Cost</th>
                <th className="py-3 pr-4 font-medium tracking-wide uppercase">Grounded</th>
                <th className="py-3 pr-4 font-medium tracking-wide uppercase">Cached</th>
              </tr>
            </thead>
            <tbody>
              {state.rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => router.push(`/activity/${row.id}`)}
                  className="cursor-pointer border-b border-black/5 hover:bg-black/[0.03] dark:border-white/5 dark:hover:bg-white/[0.03]"
                >
                  <td className="py-3 pr-4 whitespace-nowrap">
                    {/* This link is the row's real anchor, so keyboard and
                        middle-click work. Mouse clicks land on the row's
                        onClick, and stopPropagation keeps one click from
                        firing both. */}
                    <Link
                      href={`/activity/${row.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="hover:text-accent hover:underline"
                    >
                      {new Date(row.created_at).toLocaleString()}
                    </Link>
                  </td>
                  <td className="py-3 pr-4">{row.request_type}</td>
                  <td className="py-3 pr-4">{row.latency_ms} ms</td>
                  <td className="py-3 pr-4">
                    {row.estimated_cost_usd !== null
                      ? `$${row.estimated_cost_usd.toFixed(4)}`
                      : "—"}
                  </td>
                  <td className="py-3 pr-4">
                    {row.grounded === null ? (
                      "—"
                    ) : (
                      <Badge variant={row.grounded ? "success" : "danger"}>
                        {row.grounded ? "yes" : "no"}
                      </Badge>
                    )}
                  </td>
                  <td className="py-3 pr-4">
                    {row.cached && <Badge variant="secondary">cached</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <NextSteps
        links={[
          {
            href: "/evaluation-lab",
            label: "Evaluation Lab",
            note: "See how these requests get measured.",
          },
          {
            href: "/architecture",
            label: "Architecture",
            note: "See what decided each outcome, and why.",
          },
        ]}
      />
    </div>
  );
}
