import Link from "next/link";
import type { RefundEvaluateResponse } from "@/lib/api";
import { Badge, type BadgeTone } from "@/components/Badge";

const STATUS_TONE: Record<string, BadgeTone> = {
  approved: "success",
  denied: "danger",
  requires_manager_approval: "warning",
  flagged_for_review: "warning",
  could_not_process: "neutral",
};

// Shared between the free-form refund box and refund-type ScenarioCards —
// same response shape, same rendering.
export function RefundResult({ result }: { result: RefundEvaluateResponse }) {
  return (
    <div className="flex flex-col gap-4 rounded-md border border-black/10 p-4 dark:border-white/10">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={STATUS_TONE[result.status] ?? "neutral"}>{result.status}</Badge>
        {result.rule_applied !== null && (
          <span className="text-xs text-gray-500 dark:text-gray-400">rule {result.rule_applied}</span>
        )}
      </div>

      <p className="text-sm">{result.reasoning}</p>

      {Object.keys(result.extracted_fields).length > 0 && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <p className="font-medium text-gray-700 dark:text-gray-300">Extracted fields</p>
          <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
            {Object.entries(result.extracted_fields).map(([key, value]) => (
              <div key={key} className="contents">
                <dt className="font-mono">{key}</dt>
                <dd>{value === null || value === undefined ? "—" : String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <Link
        href={`/activity/${result.request_log_id}`}
        className="self-start text-xs font-medium underline underline-offset-2 hover:no-underline"
      >
        View execution trace
      </Link>
    </div>
  );
}
