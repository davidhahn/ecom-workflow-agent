import Link from "next/link";
import type { RefundEvaluateResponse } from "@/lib/api";
import { Badge, type BadgeVariant } from "@/components/ui/badge";

const STATUS_VARIANT: Record<string, BadgeVariant> = {
  approved: "success",
  denied: "danger",
  requires_manager_approval: "warning",
  flagged_for_review: "warning",
  could_not_process: "secondary",
};

// Shared between the free-form refund box and refund-type ScenarioCards:
// same response shape, same rendering. traceHref defaults to this result's
// own trace. Pass null to hide the link entirely, for a captured snapshot
// whose request_log_id points at a row the demo DB may have already reset.
export function RefundResult({
  result,
  traceHref = `/activity/${result.request_log_id}`,
}: {
  result: RefundEvaluateResponse;
  traceHref?: string | null;
}) {
  return (
    <div className="flex flex-col gap-5 rounded-md border border-black/10 p-6 dark:border-white/10">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={STATUS_VARIANT[result.status] ?? "secondary"}>{result.status}</Badge>
        {result.rule_applied !== null && (
          <span className="text-xs text-gray-500 dark:text-gray-400">rule {result.rule_applied}</span>
        )}
      </div>

      <p className="max-w-prose text-base leading-relaxed">{result.reasoning}</p>

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

      {traceHref !== null && (
        <Link
          href={traceHref}
          className="self-start text-xs font-medium text-accent underline underline-offset-2 hover:no-underline"
        >
          View execution trace
        </Link>
      )}
    </div>
  );
}
