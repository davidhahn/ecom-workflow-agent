import { Markdown } from "@/components/Markdown";
import { NextSteps } from "@/components/NextSteps";
import { getAllEvalReports, getEvalResults, getExperimentMetadata } from "@/lib/evals";
import { GITHUB_REPO_URL } from "@/lib/site";

// Summary line per report, shown on the collapsed row so a reader can decide
// what to expand without opening everything.
const REPORT_SUMMARIES: Record<string, { title: string; hook: string }> = {
  "frozen_suite.md": {
    title: "Dataset and comparison scope",
    hook: "Which cases belong to the reference dataset and which reports can be compared.",
  },
  "primary_results.md": {
    title: "Before-and-after results",
    hook: "How the SQL prompt and retrieval threshold affected the tested cases.",
  },
  "experiment_history.md": {
    title: "Experiments and decisions",
    hook: "What I tested, what happened, and which changes I kept or deferred.",
  },
  "measurement_context.md": {
    title: "Run configurations",
    hook: "The models, embedding providers, and settings used for each experiment.",
  },
  "findings.md": {
    title: "Findings",
    hook: "The SQL errors, citation-check limitations, and deployed failures I investigated.",
  },
  "methodology.md": {
    title: "Evaluation method",
    hook: "How answers are scored, how I checked the judge, and how to run the suite.",
  },
};

const CATEGORY_LABELS: Record<string, string> = {
  sql: "SQL queries", sql_semantic: "SQL correctness", rag: "Policy retrieval",
  mixed: "Combined data and policy answers", request_faithfulness: "Unsupported-action responses",
  groundedness: "Policy citation checks", topic_coverage: "Topic coverage",
  permission: "Permissions", prompt_injection: "Prompt injection",
  refund_evaluator: "Refund rules", resilience: "Failure handling",
};

export default function EvaluationLabPage() {
  const results = getEvalResults();
  const experiment = getExperimentMetadata();
  const reports = getAllEvalReports();
  const skippedCaseCount = Object.keys(results.skipped_case_ids).length;

  return (
    <div className="flex flex-col gap-12">
      <div>
        <h1 className="text-3xl font-semibold">Evaluation Lab</h1>
        <p className="mt-3 max-w-prose text-base text-gray-600 dark:text-gray-300">
          I use these evaluations to check changes against known answers and expected behavior.
          The reports below show what improved, what failed, and how the findings changed what I built.
        </p>
      </div>

      <section aria-labelledby="comparison-heading">
        <h2 id="comparison-heading" className="text-xl font-semibold">Before-and-after results</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr><th className="p-2">Capability</th><th className="p-2">Before</th><th className="p-2">After</th><th className="p-2">Scope</th></tr></thead>
            <tbody>
              <tr><td className="p-2">SQL correctness</td><td className="p-2">14/21 (67%)</td><td className="p-2">21/21 (100%)</td><td className="p-2">Seven cases, three runs per configuration</td></tr>
              <tr><td className="p-2">Policy retrieval</td><td className="p-2">7/12 (58%)</td><td className="p-2">11/12 (92%)</td><td className="p-2">Twelve cases, unchanged results across three runs per configuration</td></tr>
              <tr><td className="p-2">Combined data and policy answers</td><td className="p-2">7/8</td><td className="p-2">7/8</td><td className="p-2">Eight cases, one run per configuration; the failing case changed</td></tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 max-w-prose text-sm text-gray-600 dark:text-gray-300">These comparisons used the local embedding model. Production uses Voyage and needs a separate evaluation.</p>
        <a className="mt-3 inline-block text-sm underline underline-offset-2" href="#primary_results">Read the comparison and its sources ↓</a>
      </section>

      <div>
        <h2 className="text-xl font-semibold">Saved run: August 22, 2026</h2>
        <p className="mt-3 text-3xl font-semibold">
          {results.overall.passed}/{results.overall.total}
          <span className="ml-2 text-lg font-normal text-gray-500 dark:text-gray-400">
            cases passed ({results.overall.pass_rate.toFixed(1)}%)
          </span>
        </p>
        <p className="mt-2 max-w-prose text-base text-gray-600 dark:text-gray-300">
          This snapshot shows one recorded run. Its totals cover the cases that executed, with
          skipped cases listed under Run details. The comparisons above draw on separately recorded experiments.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-black/10 text-xs text-gray-500 dark:border-white/10 dark:text-gray-400">
              <th className="py-3 pr-4 font-medium">Capability</th>
              <th className="py-3 pr-4 font-medium">Cases run</th>
              <th className="py-3 pr-4 font-medium">Passed</th>
              <th className="py-3 pr-4 font-medium">Pass rate</th>
              <th className="py-3 pr-4 font-medium">What it tests</th>

            </tr>
          </thead>
          <tbody>
            {results.categories.map((c) => (
              <tr key={c.category} className="border-b border-black/5 dark:border-white/5">
                <td className="py-3 pr-4">{CATEGORY_LABELS[c.category] ?? c.category}<span className="mt-1 block font-mono text-xs text-gray-500">{c.category}</span></td>
                <td className="py-3 pr-4">{c.n}</td>
                <td className="py-3 pr-4">
                  {c.passed}/{c.n}
                </td>
                <td className="py-3 pr-4">{c.pass_rate.toFixed(1)}%</td>
                <td className="py-3 pr-4 text-gray-600 dark:text-gray-300">{c.what_it_tests}</td>

              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 max-w-prose text-sm text-gray-500 dark:text-gray-400">
          Categories contain 2–12 cases. These results describe behavior on the tested scenarios.
          Repeated runs help assess consistency, but broader coverage requires additional cases.
        </p>
      </div>

      <details className="rounded-md border border-black/10 dark:border-white/10">
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium">
          Run details and skipped cases
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
          {(results.skipped_categories.length > 0 || skippedCaseCount > 0) && (
            <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
              Skipped this run: {results.skipped_categories.join(", ")}. {skippedCaseCount}{" "}
              individual case{skippedCaseCount === 1 ? "" : "s"} skipped too, each for a stated
              reason recorded in <code>results.json</code>.
            </p>
          )}
        </div>
      </details>

      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">Reports</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Start with the comparisons to see what changed. Each report includes the evidence needed to interpret its results.
          </p>
        </div>
        {reports.map((report) => {
          const summary = REPORT_SUMMARIES[report.name];
          return (
            <details
              key={report.name}
              id={report.name.replace(/\.md$/, "")}
              className="scroll-mt-20 overflow-hidden rounded-md border border-black/10 dark:border-white/10"
            >
              <summary className="cursor-pointer select-none px-5 py-4">
                <span className="text-base font-medium">{summary.title}</span>
                <span className="ml-2 font-mono text-xs text-gray-400 dark:text-gray-500">
                  evals/{report.name}
                </span>
                <span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">
                  {summary.hook}
                </span>
              </summary>
              <div className="border-t border-black/10 bg-black/[0.015] px-5 py-6 dark:border-white/10 dark:bg-white/[0.02]">
                <Markdown content={report.content} />
              </div>
            </details>
          );
        })}
      </div>

      <NextSteps
        links={[
          {
            href: "/architecture",
            label: "Architecture",
            note: "See how the execution controls and answer checks work.",
          },
          { href: `${GITHUB_REPO_URL}/blob/main/CASE_STUDY.md`, label: "Case study", note: "Follow the investigation and the decisions it changed." },
        ]}
      />
    </div>
  );
}
