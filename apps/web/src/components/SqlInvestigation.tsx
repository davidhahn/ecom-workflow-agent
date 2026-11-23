import { getSqlInvestigation, SQL_CALIBRATION_SOURCE, SQL_FIXED_SOURCE } from "@/lib/sql-investigation";
import type { getPublicEvalReport } from "@/lib/public-eval-report";
import { GITHUB_REPO_URL } from "@/lib/site";

function Source({ file, children }: { file: string; children: React.ReactNode }) {
  return <a href={`${GITHUB_REPO_URL}/blob/main/${file}`} className="text-accent underline underline-offset-2">{children}</a>;
}

export function SqlInvestigation({ regression }: { regression: ReturnType<typeof getPublicEvalReport>["regression"] }) {
  const evidence = getSqlInvestigation();
  const [electronics, home] = evidence.examples;
  return (
    <section id="sql-investigation" className="scroll-mt-24 space-y-8" aria-labelledby="regression">
      <header className="space-y-3">
        <p className="text-sm text-gray-500 dark:text-gray-400">SQL investigation · Safe to run didn’t mean correct</p>
        <h2 id="regression" className="text-2xl font-semibold">The query ran successfully. The refund rate was wrong.</h2>
        <p className="max-w-prose">An operations team could use a refund rate to decide which products need attention. My agent returned {electronics.beforeRate.toFixed(2)}% for Electronics. The independently checked answer was {electronics.afterRate.toFixed(2)}%. The query had stayed within its permissions, but it had calculated a different metric.</p>
      </header>

      <div className="rounded-lg border border-black/10 p-6 dark:border-white/10">
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">The actual request</p>
        <blockquote className="mt-3 max-w-prose text-lg">{electronics.request}</blockquote>
        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <h3 className="font-semibold">Before: {electronics.beforeRate.toFixed(2)}%</h3>
            <p className="text-sm">{String(electronics.before.rows[0].total_refunds)} refund records / {String(electronics.before.rows[0].total_order_items)} order lines</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Baseline calibration, run 1. Status: {electronics.before.status}; structural checks passed. One captured query, not the whole comparison.</p>
          </div>
          <div className="space-y-2">
            <h3 className="font-semibold">After: {electronics.afterRate.toFixed(2)}%</h3>
            <p className="text-sm">{String(electronics.after.rows[0].units_refunded)} approved refunded units / {String(electronics.after.rows[0].units_sold)} units sold</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">August 22, 2026 local run, SQL prompt {electronics.after.prompt_version}. One captured query through the direct SQL endpoint.</p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-semibold">How I established the cause</h3>
        <p className="max-w-prose">I checked the expected answer separately in Postgres and compared it against the 20 raw order-item rows. Some rows contained more than one unit, giving 23 units sold. Reading the generated SQL showed it used COUNT(DISTINCT oi.id), so it counted each order line once and lost those quantities.</p>
        <p className="max-w-prose">All 10 Electronics refunds were already approved. A missing status filter wasn’t the cause of this particular mismatch. The Home case exposed both problems: it counted a denied refund and used order-line counts. That returned {home.beforeRate.toFixed(2)}% instead of {home.afterRate.toFixed(2)}%.</p>
        <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">The baseline calibration recorded {evidence.structuralPassed}/{evidence.calibrationCount} structural passes, but only {evidence.correct} correct outcomes: {evidence.wrong} calculations were wrong, and {evidence.unscored} valid query was rejected before it could be scored. I had to inspect the SQL and full rows, not just trust a success status or the failure summary’s scalar value.</p>
        <details className="rounded-lg border border-black/10 p-5 dark:border-white/10">
          <summary className="cursor-pointer font-medium">See the actual queries, returned rows, and independent checks</summary>
          <div className="mt-6 space-y-10">
            {evidence.examples.map((example) => (
              <div key={example.id} className="min-w-0 space-y-5">
                <h4 className="font-semibold">{example.request}</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">Case: <code className="wrap-anywhere">{example.id}</code>. These query captures come from the baseline calibration and the August 22 run; they are not the per-attempt traces of the ablation comparison below.</p>
                {[
                  { label: "Before · baseline calibration, run 1", sql: example.before.generated_sql, rows: example.before.rows, file: SQL_CALIBRATION_SOURCE },
                  { label: `After · August 22 local run, prompt ${example.after.prompt_version}`, sql: example.after.sql_executed, rows: example.after.rows, file: SQL_FIXED_SOURCE },
                ].map((capture) => (
                  <div key={capture.label} className="min-w-0 space-y-3">
                    <p className="text-sm font-medium">{capture.label}</p>
                    <pre className="overflow-x-auto rounded-md bg-black/5 p-4 text-xs leading-relaxed whitespace-pre-wrap wrap-anywhere dark:bg-white/5"><code>{capture.sql}</code></pre>
                    <pre className="overflow-x-auto rounded-md bg-black/5 p-4 text-xs leading-relaxed dark:bg-white/5"><code>{JSON.stringify(capture.rows, null, 2)}</code></pre>
                    <p className="text-sm"><Source file={`evals/${capture.file}`}>Open the saved query and result</Source></p>
                  </div>
                ))}
                <p className="max-w-prose text-sm"><strong>Recorded independent check:</strong> {example.derivation}</p>
              </div>
            ))}
          </div>
        </details>
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-semibold">What I changed</h3>
        <p className="max-w-prose">I added assertions against the independently calculated values and clarified the SQL prompt with a worked example: use SUM(quantity), and count only approved refunds toward the rate. I also fixed a validator bug that sometimes rejected a valid COUNT(*) expression.</p>
        <p className="max-w-prose">A later deployed Ask check exposed another gap: Ask generated SQL with its own prompt, bypassing the corrected direct-SQL prompt. The metric instructions now live in one shared module used by both paths. The Ask prompt and cache key were versioned so an old cached answer wouldn’t hide the change.</p>
        <p className="text-sm"><Source file="DECISIONS.md#decision-37">Original fix and validator tradeoff</Source> · <Source file="DECISIONS.md#61-share-metric-definitions-with-the-ask-sql-generation-path">Later Ask-path fix</Source> · <Source file="apps/api/app/query/metric_instructions.py">Shared metric instructions</Source></p>
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-semibold">What improved, and what that still doesn’t prove</h3>
        <p className="text-2xl font-semibold">{regression[0].passed}/{regression[0].n} → {regression[1].passed}/{regression[1].n} correct SQL outcomes</p>
        <p className="max-w-prose">The saved ablation comparison covers {regression[0].distinct} different questions, each run {regression[0].runs} times per configuration. It supports an improvement on that workload. It isn’t 21 independent questions or proof that future queries will be correct.</p>
        <p className="max-w-prose">The comparison uses the “baseline” and “+ bounded failure handling” configurations. Several settings changed, so I can’t attribute the whole gain to the prompt alone. The count includes a validator rejection as well as incorrect calculations. The experiment also didn’t record its commit, which limits reproducibility.</p>
        <p className="max-w-prose">These were local tests through the direct SQL endpoint. They don’t establish the current deployed Ask workflow’s accuracy or whether its final written answer uses the numbers correctly. The next check is to repeat the calculation suite through Ask with the current configuration, cache bypassed, against independently calculated answers.</p>
        <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">The later August 22 suite still marked the average-days-to-refund case as failing. That result needs its own query, expected-value, and fixture review; a perfect score in one comparison didn’t establish that every later run would pass.</p>
        <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm">
          <Source file="evals/ablation_raw.json">Raw before/after outcomes</Source>
          <Source file="evals/primary_results.md">Comparison and sample scope</Source>
          <Source file="evals/measurement_context.md">Experiment configurations</Source>
          <a href="#findings-finding-2-sql-calculation-errors" className="text-accent underline underline-offset-2">Original investigation notes</a>
        </div>
      </div>
    </section>
  );
}
