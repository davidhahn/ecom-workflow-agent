import { Badge } from "@/components/Badge";
import { Markdown } from "@/components/Markdown";
import { getAllEvalReports, getEvalResults, getExperimentMetadata } from "@/lib/evals";

// Summary line per report, shown on the collapsed row so a reader can decide
// what to expand without opening everything.
const REPORT_SUMMARIES: Record<string, { title: string; hook: string }> = {
  "frozen_suite.md": {
    title: "Frozen suite",
    hook: "The 79-case reference point every comparison on this page traces back to.",
  },
  "primary_results.md": {
    title: "Primary results",
    hook: "Baseline against current, with a source for every number.",
  },
  "experiment_history.md": {
    title: "Experiment history",
    hook: "One row per change: the measured effect, then the decision it led to.",
  },
  "measurement_context.md": {
    title: "Measurement context",
    hook: "The exact configuration behind each result set, and where local eval and production differ.",
  },
  "findings.md": {
    title: "Findings",
    hook: "Five investigations, each starting from something that looked wrong.",
  },
  "methodology.md": {
    title: "Methodology",
    hook: "How the numbers were made, and the command that reproduces them.",
  },
};

export default function EvaluationLabPage() {
  const results = getEvalResults();
  const experiment = getExperimentMetadata();
  const reports = getAllEvalReports();
  const skippedCaseCount = Object.keys(results.skipped_case_ids).length;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold">Evaluation Lab</h1>
        <p className="mt-2 text-3xl font-semibold">
          {results.overall.passed}/{results.overall.total}
          <span className="ml-2 text-lg font-normal text-gray-500 dark:text-gray-400">
            cases passed ({results.overall.pass_rate.toFixed(1)}%)
          </span>
        </p>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Every number on this page comes from one committed eval run and the reports written from
          it.
        </p>
        <p className="mt-3 font-mono text-xs text-gray-500 dark:text-gray-400">
          {experiment.application_model} · judge {experiment.judge_model} · dataset{" "}
          {experiment.eval_dataset_version} · commit {experiment.git_commit} · cache{" "}
          {experiment.cache_bypassed ? "bypassed" : "used"} · run {results.timestamp}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-black/10 text-xs text-gray-500 dark:border-white/10 dark:text-gray-400">
              <th className="py-2 pr-4 font-medium">Category</th>
              <th className="py-2 pr-4 font-medium">n</th>
              <th className="py-2 pr-4 font-medium">Passed</th>
              <th className="py-2 pr-4 font-medium">Pass rate</th>
              <th className="py-2 pr-4 font-medium">What it tests</th>
              <th className="py-2 pr-4 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {results.categories.map((c) => (
              <tr key={c.category} className="border-b border-black/5 dark:border-white/5">
                <td className="py-2 pr-4 font-mono">{c.category}</td>
                <td className="py-2 pr-4">{c.n}</td>
                <td className="py-2 pr-4">
                  {c.passed}/{c.n}
                </td>
                <td className="py-2 pr-4">{c.pass_rate.toFixed(1)}%</td>
                <td className="py-2 pr-4 text-gray-600 dark:text-gray-300">{c.what_it_tests}</td>
                <td className="py-2 pr-4">
                  {!c.comparison_ready && (
                    <span title="This category has too few cases to trust as a percentage. See the note below the table.">
                      <Badge tone="neutral">
                        too few cases to compare (n&lt;{results.comparison_readiness.threshold_n})
                      </Badge>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          One run each, from <code>evals/results/{results.timestamp}</code>. The Primary Results
          report below draws on repeated runs for some categories, so check its sourcing notes
          before comparing a number here against a number there.
        </p>
        <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          <Markdown content={results.comparison_readiness.note} />
        </div>
      </div>

      <details className="rounded-md border border-black/10 dark:border-white/10">
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium">
          Run details: skips and environment
        </summary>
        <div className="border-t border-black/10 px-4 py-3 text-sm dark:border-white/10">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-3">
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Application model</dt>
              <dd className="font-mono">{experiment.application_model}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Judge model</dt>
              <dd className="font-mono">{experiment.judge_model}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Dataset version</dt>
              <dd className="font-mono">{experiment.eval_dataset_version}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Commit</dt>
              <dd className="font-mono">{experiment.git_commit}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Cache bypassed</dt>
              <dd className="font-mono">{experiment.cache_bypassed ? "yes" : "no"}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Run</dt>
              <dd className="font-mono">{results.timestamp}</dd>
            </div>
          </dl>
          {results.skipped_categories.length > 0 && (
            <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
              Skipped this run: {results.skipped_categories.join(", ")}. {skippedCaseCount}{" "}
              individual case{skippedCaseCount === 1 ? "" : "s"} skipped too, each for a stated
              reason recorded in <code>results.json</code>.
            </p>
          )}
        </div>
      </details>

      <div className="flex flex-col gap-3">
        <div>
          <h2 className="text-lg font-semibold">Reports</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            The six committed reports behind the table above. Each one expands in place.
          </p>
        </div>
        {reports.map((report) => {
          const summary = REPORT_SUMMARIES[report.name];
          return (
            <details
              key={report.name}
              className="rounded-md border border-black/10 dark:border-white/10"
            >
              <summary className="cursor-pointer select-none px-4 py-3">
                <span className="text-sm font-medium">{summary.title}</span>
                <span className="ml-2 font-mono text-xs text-gray-400 dark:text-gray-500">
                  evals/{report.name}
                </span>
                <span className="mt-0.5 block text-xs text-gray-500 dark:text-gray-400">
                  {summary.hook}
                </span>
              </summary>
              <div className="border-t border-black/10 px-4 py-4 dark:border-white/10">
                <Markdown content={report.content} />
              </div>
            </details>
          );
        })}
      </div>
    </div>
  );
}
