import Link from "next/link";
import type { AnalyzeResponse } from "@/lib/api";
import { Badge } from "@/components/Badge";
import { Markdown } from "@/components/Markdown";

// Shared between the Ask page and analyze-type ScenarioCards — same
// response shape, same rendering.
export function AnalyzeResult({ result }: { result: AnalyzeResponse }) {
  if (result.incomplete) {
    return (
      <div className="flex flex-col gap-1 rounded-md border-2 border-amber-400 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
        <p className="font-semibold">Unable to complete this request</p>
        <p>{result.answer}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 rounded-md border border-black/10 p-4 dark:border-white/10">
      <div className="flex flex-wrap gap-2">
        <Badge tone={result.sql_used ? "success" : "neutral"}>
          {result.sql_used ? "SQL used" : "SQL not used"}
        </Badge>
        <Badge tone={result.rag_used ? "success" : "neutral"}>
          {result.rag_used ? "Policy lookup used" : "Policy lookup not used"}
        </Badge>
        <Badge tone={result.grounded ? "success" : "danger"}>
          {result.grounded ? "Grounded" : "Ungrounded claims detected"}
        </Badge>
        {result.cached && <Badge tone="neutral">Cached</Badge>}
      </div>

      {!result.grounded && (
        <div className="flex flex-col gap-1 rounded-md border-2 border-red-400 bg-red-50 p-4 text-sm text-red-900 dark:border-red-700 dark:bg-red-950/40 dark:text-red-200">
          <p className="font-semibold">This response contains an unverified claim</p>
          <p>
            At least one cited policy rule wasn&apos;t among what was actually retrieved for this
            request. The answer is still shown below — treat it with caution until this is checked.
          </p>
          {result.ungrounded_claims.length > 0 && (
            <ul className="mt-1 list-disc pl-4">
              {result.ungrounded_claims.map((claim) => (
                <li key={claim}>{claim}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {result.topic_coverage_warning && (
        <div className="flex flex-col gap-1 rounded-md border-2 border-red-400 bg-red-50 p-4 text-sm text-red-900 dark:border-red-700 dark:bg-red-950/40 dark:text-red-200">
          <p className="font-semibold">This response may reference unavailable data</p>
          <p>
            This response may reference shipment/delivery data not available to the current
            toolset. The answer is still shown below — treat it with caution until this is checked.
          </p>
        </div>
      )}

      <Markdown content={result.answer} />

      {result.sources.length > 0 && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <p className="font-medium text-gray-700 dark:text-gray-300">Sources</p>
          <ul className="mt-1 list-disc pl-4">
            {result.sources.map((source, i) => (
              <li key={i}>
                {source.source_doc}
                {source.rule_number !== null ? ` — rule ${source.rule_number}` : ""}
              </li>
            ))}
          </ul>
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
