import Link from "next/link";
import { SqlInvestigation } from "@/components/SqlInvestigation";
import { getPublicEvalReport, REPORT_RUN } from "@/lib/public-eval-report";
import { ReportDisclosure } from "@/components/ReportDisclosure";
import { Markdown } from "@/components/Markdown";
import { getAllEvalReports } from "@/lib/evals";
import { GITHUB_REPO_URL } from "@/lib/site";

export const metadata = { title: "Results & evidence", description: "What testing an e-commerce operations agent revealed about wrong calculations, incomplete checks, and the work still needed." };
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

const LABELS: Record<string, string> = {
  sql: "SQL queries", sql_semantic: "SQL calculations", rag: "Policy retrieval",
  mixed: "Combined data and policy answers", refund_evaluator: "Refund rules",
  groundedness: "Policy citation checks", topic_coverage: "Unsupported-topic checks",
  permission: "Permissions", prompt_injection: "Prompt injection",
  request_faithfulness: "Unsupported-action responses", resilience: "Failure handling",
  invoice_evaluator: "Invoice workflow", ticket_evaluator: "Ticket workflow",
};
const seconds = (ms: number | null) => ms === null ? "—" : `${(ms / 1000).toFixed(3)} s`;
const cell = "px-3 py-3 align-top";
const table = "w-full text-left text-sm [&_th]:font-medium [&_tr]:border-b [&_tr]:border-black/10 dark:[&_tr]:border-white/10";
function Source({ file, children }: { file: string; children: React.ReactNode }) {
  return <a className="text-accent underline underline-offset-2" href={`${GITHUB_REPO_URL}/blob/main/evals/${file}`}>{children}</a>;
}

export default function EvaluationLabPage() {
  const report = getPublicEvalReport();
  const { results, experiment } = report;
  const reports = getAllEvalReports();
  return (
    <article className="flex flex-col gap-16">
      <header className="flex flex-col gap-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">E-commerce operations agent · Evaluation report</p>
        <h1 className="text-3xl font-semibold sm:text-4xl">How I check whether the agent gives the right answer</h1>
        <p className="max-w-prose text-gray-600 dark:text-gray-300">I built this assistant to answer questions about orders, refund rates, and company policies, and to check whether a refund qualifies. For someone using it, the important part is whether the answer is correct and whether they can see how it was reached.</p>
        <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">The demo uses seeded sample records and evaluates refund eligibility without issuing refunds. I haven&apos;t measured customer adoption or business savings.</p>
        <div className="flex flex-wrap gap-4 text-sm">
          <Link className="font-medium text-accent underline" href="/scenarios">Try a live scenario →</Link>
          <a className="text-accent underline" href="#coverage">See the main results ↓</a>
        </div>
      </header>


      <section className="space-y-6" aria-labelledby="example">
        <h2 id="example" className="text-xl font-semibold">One request, from question to result</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Recorded direct-SQL example · August 22 local run · SQL prompt v2 · not a live Ask response</p>
        <div className="rounded-lg border border-black/10 p-5 dark:border-white/10">
          <p className="text-sm font-medium">Request</p>
          <blockquote className="mt-2 max-w-prose">{report.example.request}</blockquote>
          <ol className="my-5 max-w-prose list-decimal space-y-2 pl-5 text-sm">
            <li>The model proposes a database query for the question.</li>
            <li>Code checks access and query cost before running it with read-only permissions.</li>
            <li>The query counts units sold and approved refunded units. The test compares the result with a separately calculated answer.</li>
          </ol>
          <p className="text-sm font-medium">Recorded result</p>
          <p className="mt-2 text-2xl font-semibold">{report.example.refunded} approved refunded units / {report.example.sold} units sold = {report.example.rate.toFixed(2)}%</p>
          <p className="mt-3 max-w-prose text-sm text-gray-500 dark:text-gray-400">This matched the independent answer for this case. Safe execution alone would not establish that the calculation was correct.</p>
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          <Link className="text-accent underline" href="/ask">Ask your own data question →</Link>
          <Source file={`results/${REPORT_RUN}/results.json`}>Recorded query and result</Source>
        </div>
      </section>

      <section className="space-y-6" aria-labelledby="coverage">
        <h2 id="coverage" className="text-xl font-semibold">What passed, what failed, and what didn’t run</h2>
        <div className="rounded-lg border border-black/10 p-5 dark:border-white/10">
          <p className="text-2xl font-semibold">{results.overall.passed}/{results.overall.total} tests passed ({(100 * results.overall.passed / results.overall.total).toFixed(1)}%)</p>
          <p className="mt-2 text-sm">{report.datasetCount} cases in the dataset · {report.categoryCount} categories · {report.skipped} not run · {results.overall.failed} failures</p>
          <p className="mt-3 max-w-prose text-sm text-gray-500 dark:text-gray-400">These results come from the August 22 local run. They cover the questions tested then; they don’t establish how the current deployed app handles every question. The run details and source files are below.</p>
        </div>
        <p className="max-w-prose">I have {report.datasetCount} cases across {report.categoryCount} categories. This run covered 11 categories. The test code for 8 invoice cases and 6 ticket cases wasn’t implemented, and 3 injection cases needed inputs or workflows the runner couldn’t handle. Those 17 cases are left out of the pass rate.</p>
        <p className="text-sm"><Source file="cases.json">Dataset</Source> · <Source file={`results/${REPORT_RUN}/results.json`}>Saved results and skip reasons</Source></p>
        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { category: "sql_semantic", note: "Four calculation cases through the direct SQL endpoint; this does not validate every Ask query." },
            { category: "mixed", note: "Eight combined data/policy answers, with one failure. Scoring includes a model grader." },
            { category: "refund_evaluator", note: "Twelve rule checks with known inputs. They bypass the model reading the customer’s message." },
          ].map(({ category, note }) => {
            const row = report.categories.find((item) => item.category === category)!;
            return <div key={category} className="rounded-md border border-black/10 p-4 dark:border-white/10">
              <h3 className="font-medium">{LABELS[category]}</h3>
              <p className="mt-2 text-2xl font-semibold">{row.passed}/{row.scored}</p>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{note}</p>
            </div>;
          })}
        </div>
        <details className="rounded-md border border-black/10 p-4 dark:border-white/10">
          <summary className="cursor-pointer font-medium">All 13 categories and skipped coverage</summary>
        <div className="overflow-x-auto"><table className={table}>
          <caption className="mb-3 text-left text-sm text-gray-500">Results from the August 22 run. Refund-rule tests supply known fields directly, so they don’t test whether the model understood the customer’s message. Policy retrieval tests check which passages were found, not whether the final answer used them correctly.</caption>
          <thead><tr>{["Area tested", "Cases", "Run", "Passed / run", "Not run"].map((label) => <th key={label} className={cell}>{label}</th>)}</tr></thead>
          <tbody>{report.categories.map((row) => <tr key={row.category}>
            <th scope="row" className={cell}>{LABELS[row.category]}</th>
            <td className={cell}>{row.defined}</td><td className={cell}>{row.scored}</td>
            <td className={cell}>{row.scored ? `${row.passed}/${row.scored} (${(100 * row.passed / row.scored).toFixed(1)}%)` : "Not run"}</td>
            <td className={cell}>{row.skipped}</td>
          </tr>)}</tbody>
        </table></div>
        </details>
        <p className="max-w-prose text-sm text-gray-500">Two cases failed: a calculation of the average time before a refund request, and an answer that combined order data with policy. The query, answer, and scoring need to be read together to understand those failures. A failed test can also expose a problem with the expected answer or the test setup.</p>
      </section>

      <SqlInvestigation regression={report.regression} />


      <section className="space-y-6" aria-labelledby="judge">
        <h2 id="judge" className="text-xl font-semibold">How I checked the model grading the answers</h2>
        <p className="max-w-prose">Some answers need more than a numeric comparison, so I use a second model to grade them against written criteria. I compared its decisions with my own labels in two separate reviews. We agreed on {report.audits.reduce((sum, row) => sum + row.agreed, 0)} of {report.audits.reduce((sum, row) => sum + row.n, 0)} decisions. However, every answer in that sample was a passing example, including responses that correctly said an action couldn’t be performed. I still need to check how well the grader catches bad answers. These reviews are separate from the 62-case run.</p>
        <ul className="list-disc space-y-2 pl-5 text-sm">{report.audits.map((audit) => <li key={audit.file}><Source file={audit.file}>{audit.file === "labels.json" ? "Answer-grading review" : "Unsupported-action review"}</Source>: {audit.agreed}/{audit.n} decisions agree, across {audit.distinct} different questions{audit.n !== audit.distinct ? " (repeated observations of the same questions)" : ""}.</li>)}</ul>
      </section>

      <section className="space-y-6" aria-labelledby="performance">
        <h2 id="performance" className="text-xl font-semibold">How long the tests took and what the model calls cost</h2>
        <p className="max-w-prose text-sm">I calculated these figures from the same saved run, including failed tests. The median shows the middle recorded time. The p95 shows the time at or below which at least 95% of the tests finished. Each question ran once here. With only a few cases in a category, p95 is the slowest recorded time.</p>
        <p className="max-w-prose text-sm text-gray-500">These times include the test runner’s work and, for some categories, the grading model. They aren’t measurements of how long a user waits in production. Cost covers the recorded calls to the application model. It excludes grading calls, hosting, and any unrecorded cost of turning policy text into searchable vectors. Missing costs are shown as “Not recorded”; $0 means no model cost was recorded for that test.</p>
        <details className="rounded-md border border-black/10 p-4 dark:border-white/10">
          <summary className="cursor-pointer font-medium">Timing and cost by category</summary>
        <div className="overflow-x-auto"><table className={table}>
          <thead><tr>{["Area tested", "Timed cases", "Median", "p95", "Average recorded cost / case", "Cost records"].map((label) => <th key={label} className={cell}>{label}</th>)}</tr></thead>
          <tbody>{report.categories.filter((row) => row.scored).map((row) => <tr key={row.category}>
            <th scope="row" className={cell}>{LABELS[row.category]}</th><td className={cell}>{row.n}</td>
            <td className={`${cell} whitespace-nowrap`}>{seconds(row.medianMs)}</td><td className={`${cell} whitespace-nowrap`}>{seconds(row.p95Ms)}</td>
            <td className={cell}>{row.meanCost === null ? "Not recorded" : `$${row.meanCost.toFixed(5)}`}</td><td className={cell}>{row.costN}/{row.scored}</td>
          </tr>)}</tbody>
        </table></div>
        </details>
        <Source file={`results/${REPORT_RUN}/results.json`}>Per-case timing and cost records</Source>
      </section>

      <section className="space-y-3 border-t border-black/10 pt-6 dark:border-white/10">
        <h2 className="text-xl font-semibold">Where the numbers come from</h2>
        <p className="max-w-prose text-sm">The category results and timing table come from one saved run. The SQL comparison and grading reviews use separate samples, linked in their sections.</p>
        <details>
          <summary className="cursor-pointer text-sm font-medium">Run settings and source details</summary>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm">
          <li>Saved category results, timing, cost: run {REPORT_RUN}, commit {experiment.git_commit}, dataset {experiment.eval_dataset_version}, cache bypassed: {String(experiment.cache_bypassed)}.</li>
          <li>Application model: {experiment.application_model}; judge: {experiment.judge_model}. SQL prompt: {experiment.prompt_version.sql}; analyze prompt: {experiment.prompt_version.analyze}.</li>
          <li>Local embeddings with threshold 0.46, as recorded in <Source file="measurement_context.md">measurement_context.md</Source>. Production uses Voyage and needs separate measurement.</li>
          <li>Timing uses the median and nearest-rank p95, calculated within each category. Average cost uses only cases with a recorded cost; the table shows how many records were available.</li>
          <li>Current dataset byte hash: {report.currentDatasetHash}. {report.currentDatasetHash === experiment.eval_dataset_version ? "Matches the saved run's dataset hash." : "Differs from the saved run; current definitions must not be treated as the historical dataset without review."}</li>
          <li>Judge audit: the two linked label files, separate samples with 33 total verdicts. Those files do not contain a dataset hash, run ID, or model configuration; their provenance is less complete than the saved suite run. Ablation: seven SQL questions × three runs per configuration; its commit was not recorded in the raw artifact.</li>
          </ul>
        </details>
        <p className="text-sm"><Source file={`results/${REPORT_RUN}/experiment.json`}>Saved run configuration</Source> · <a className="text-accent underline" href="#source-reports">Detailed reports and methodology ↓</a></p>
      </section>

      <section id="source-reports" className="scroll-mt-20 space-y-4">
        <h2 className="text-xl font-semibold">Source reports</h2>
        <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">Open a report for the full experiments, failure investigations, or scoring method. The summaries above are enough to follow the main findings.</p>
        {reports.map((report) => {
          const summary = REPORT_SUMMARIES[report.name];
          return (
            <ReportDisclosure key={report.name} id={report.name.replace(/\.md$/, "")}>
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
                <Markdown content={report.content} headingPrefix={report.name.replace(/\.md$/, "")} />
              </div>
            </ReportDisclosure>
          );
        })}
      </section>

      <section className="rounded-lg border border-black/10 p-5 dark:border-white/10">
        <h2 className="text-xl font-semibold">What I need to measure next</h2>
        <p className="mt-3 max-w-prose">The next check is to repeat the calculation tests through the Ask workflow people actually use, with the current deployed settings and cached answers turned off. I’ll compare the results with independently calculated answers and record the time and model cost for each attempt. The two live checks after the prompt fix returned the right values, but I need repeated results before treating that as broader evidence.</p>
      </section>
    </article>
  );
}
