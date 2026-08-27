import Link from "next/link";
import { Badge } from "@/components/Badge";
import { ScenarioDemo } from "@/components/ScenarioDemo";
import { RESPONSIBILITY_ROWS } from "@/lib/architecture";
import { getEvalResults } from "@/lib/evals";

export default function HomePage() {
  const results = getEvalResults();

  return (
    <div className="flex flex-col gap-12">
      <div className="flex flex-col gap-5">
        <p className="max-w-prose text-lg text-gray-500 dark:text-gray-400">
          Every model gets something wrong eventually. This is how you&apos;d know.
        </p>
        <h1 className="text-3xl leading-tight font-semibold sm:text-4xl">
          An ops agent that shows its work
        </h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          Ask it a question about refund data or policy, or send it a real refund request. Claude
          reads the request and proposes an answer. Separate code checks that answer before
          anything happens, and logs exactly what it did.
        </p>

        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">Data analysis</Badge>
          <Badge tone="neutral">Policy lookup</Badge>
          <Badge tone="neutral">Refund decisions</Badge>
        </div>

        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/evaluation-lab"
            className="rounded-md border border-black/10 px-4 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
          >
            <span className="font-semibold">
              {results.overall.passed}/{results.overall.total}
            </span>{" "}
            <span className="text-gray-500 dark:text-gray-400">
              eval cases pass ({results.overall.pass_rate.toFixed(1)}%)
            </span>
          </Link>
          <Link
            href="/architecture"
            className="rounded-md border border-black/10 px-4 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
          >
            <span className="font-semibold">{RESPONSIBILITY_ROWS.length}</span>{" "}
            <span className="text-gray-500 dark:text-gray-400">
              deterministic checks run independent of the model
            </span>
          </Link>
        </div>

        <p className="max-w-prose pt-4 text-sm text-gray-500 dark:text-gray-400">
          Five scenarios below put all three to work. This is the one worth seeing first.
        </p>
      </div>

      <ScenarioDemo />
    </div>
  );
}
