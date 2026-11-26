import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { GITHUB_REPO_URL } from "@/lib/site";
import { getPublicEvalReport } from "@/lib/public-eval-report";
import { getSqlInvestigation } from "@/lib/sql-investigation";

export const metadata: Metadata = {
  description:
    "An AI assistant for e-commerce support and operations teams. See what I built, how I caught a wrong refund-rate calculation, and the evidence behind the fix.",
};

const linkStyle = "self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline";

export default function HomePage() {
  const { regression } = getPublicEvalReport();
  const { examples } = getSqlInvestigation();
  const electronics = examples[0];

  return (
    <div className="flex flex-col gap-20">
      <section className="grid items-start gap-8 lg:grid-cols-2 lg:gap-10" aria-labelledby="project-intro">
        <div className="flex flex-col gap-6">
          <p className="text-sm text-gray-500 dark:text-gray-400">E-commerce operations · Working demo and engineering case study</p>
          <h1 id="project-intro" className="text-3xl leading-tight font-semibold sm:text-5xl">
            An AI assistant for <span className="whitespace-nowrap">e-commerce</span> operations
          </h1>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            For support and operations teams: ask questions about orders and policies, check
            refund eligibility, and inspect how each result was reached.
          </p>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            I built the assistant and its evaluation workflow. One refund-rate question exposed
            a wrong answer that the query’s safety checks had missed. Here’s how I investigated it.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button asChild><Link href="/guided-demo">Start the guided demo →</Link></Button>
            <Button asChild variant="outline"><Link href="/evaluation-lab#sql-investigation">Read the SQL investigation →</Link></Button>
          </div>
          <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">
            A demo with sample orders and policies. It evaluates refund eligibility;
            it doesn’t issue refunds.
          </p>
        </div>

        <div className="flex flex-col gap-5 rounded-lg border border-black/10 bg-black/[0.02] p-5 sm:p-6 dark:border-white/10 dark:bg-white/[0.02]" aria-labelledby="example-request">
          <h2 id="example-request" className="text-lg font-semibold">One question exposed a wrong calculation</h2>
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">The actual request</p>
            <blockquote className="mt-2 text-base">“{electronics.request}”</blockquote>
          </div>
          <div className="space-y-2 border-t border-black/10 pt-4 dark:border-white/10">
            <p className="text-sm font-medium">The old query returned</p>
            <p className="text-3xl font-semibold">{electronics.beforeRate.toFixed(2)}%</p>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              {String(electronics.before.rows[0].total_refunds)} refund records / {String(electronics.before.rows[0].total_order_items)} order lines
            </p>
          </div>
          <div className="space-y-2 border-t border-black/10 pt-4 dark:border-white/10">
            <p className="text-sm font-medium">The independently checked answer</p>
            <p className="text-3xl font-semibold">{electronics.afterRate.toFixed(2)}%</p>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              {String(electronics.after.rows[0].units_refunded)} approved refunded units / {String(electronics.after.rows[0].units_sold)} units sold
            </p>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Saved local SQL records: baseline calibration and August 22, 2026 run.
            Sample data, not a live Ask result.
          </p>
          <Link href="/evaluation-lab#sql-investigation" className={linkStyle}>See the queries, results, and diagnosis →</Link>
        </div>
      </section>

      <section className="flex flex-col gap-6" aria-labelledby="scope-decisions">
        <h2 id="scope-decisions" className="text-2xl font-semibold">What I built and where I drew the boundary</h2>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          I scoped the web app and API around three tasks: order analysis, policy lookup, and
          refund eligibility. E-commerce gave me familiar business questions that still depend
          on getting calculations, policy rules, and access boundaries right.
        </p>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          The model interprets a request and proposes tools. Code decides whether a database
          query can run and applies the refund rules. I kept refund execution out of scope:
          the assistant returns an eligibility decision and the rule behind it, without moving money.
        </p>
        <div className="flex flex-wrap gap-x-6 gap-y-3">
          <Link href="/architecture" className={linkStyle}>Read the architecture and decisions →</Link>
          <Link href="/scenarios#injection-attempt" className={linkStyle}>Inspect an attempted rule override →</Link>
        </div>
      </section>

      <section className="flex flex-col gap-8" aria-labelledby="investigation-story">
        <h2 id="investigation-story" className="text-2xl font-semibold">How I traced the wrong answer</h2>
        <ol className="max-w-prose list-decimal space-y-8 pl-6">
          <li className="pl-2">
            <h3 className="text-lg font-semibold">Establish the business calculation</h3>
            <p className="mt-3 text-base text-gray-600 dark:text-gray-300">
              I checked the expected answer independently in Postgres and reviewed the order
              rows. Some lines contained multiple units. Counting each line once gave the wrong
              denominator, even though the query was safe to execute.
            </p>
          </li>
          <li className="pl-2">
            <h3 className="text-lg font-semibold">Fix the calculation and check the result</h3>
            <p className="mt-3 text-base text-gray-600 dark:text-gray-300">
              I added assertions against independently calculated values and clarified the metric
              instructions: use unit quantities and approved refunds. I also fixed a validator
              bug that sometimes rejected a valid counting expression. The Home case exposed
              another mistake: counting a denied refund as if it had happened.
            </p>
          </li>
          <li className="pl-2">
            <h3 className="text-lg font-semibold">Follow the question through the path people use</h3>
            <p className="mt-3 text-base text-gray-600 dark:text-gray-300">
              A later deployed Ask check still produced the wrong calculation. Ask used a separate
              prompt and bypassed the corrected direct-SQL prompt. I moved the metric instructions
              into a shared module and versioned the Ask prompt and cache key.
            </p>
          </li>
        </ol>
        <Link href="/evaluation-lab#sql-investigation" className={linkStyle}>Read the full investigation and its evidence →</Link>
      </section>

      <section className="flex flex-col gap-6" aria-labelledby="evidence-limits">
        <h2 id="evidence-limits" className="text-2xl font-semibold">What the evidence supports</h2>
        <div className="rounded-lg border border-black/10 p-6 sm:p-8 dark:border-white/10">
          <p className="text-xl font-semibold">{regression[0].passed}/{regression[0].n} → {regression[1].passed}/{regression[1].n} correct SQL outcomes</p>
          <p className="mt-3 max-w-prose text-base text-gray-600 dark:text-gray-300">
            {regression[0].distinct} questions, each repeated {regression[0].runs} times per configuration.
            Several settings changed, so I can’t attribute the whole improvement to one prompt edit.
            These were saved local tests of the direct SQL path, not proof of the current deployed Ask workflow’s accuracy.
          </p>
          <Link href="/evaluation-lab" className={`${linkStyle} mt-4 inline-block`}>See results, source records, and measurement limits →</Link>
        </div>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          There’s still work to do. A specific damaged-shipment policy query remained unresolved
          after changing embedding providers. The next calculation check is to repeat the suite
          through the current Ask workflow against independent answers, with cached responses bypassed.
        </p>
        <Link href="/evaluation-lab#findings-finding-5-differences-in-the-deployed-environment" className={linkStyle}>Read the remaining retrieval limitation →</Link>
        <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">
          I haven’t measured customer adoption or business savings. This case study shows the
          implementation decisions, recorded failures, and checks I can demonstrate today.
        </p>
      </section>

      <section className="flex flex-col gap-4 border-t border-black/10 pt-8 dark:border-white/10" aria-labelledby="keep-exploring">
        <h2 id="keep-exploring" className="text-xl font-semibold">Inspect the work</h2>
        <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-accent [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:no-underline">
          <Link href="/ask">Ask your own question →</Link>
          <Link href="/activity">Inspect request traces →</Link>
          <a href={GITHUB_REPO_URL} target="_blank" rel="noopener noreferrer">View the code →</a>
        </div>
      </section>
    </div>
  );
}
