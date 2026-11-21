import type { Metadata } from "next";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { GITHUB_REPO_URL } from "@/lib/site";
import { getEvalResults } from "@/lib/evals";
import { SCENARIOS } from "@/lib/scenarios";
import { getScenarioSnapshot, SNAPSHOT_CAPTURED_AT } from "@/lib/snapshots";
import type { RefundEvaluateResponse } from "@/lib/api";

export const metadata: Metadata = {
  description:
    "An e-commerce operations assistant that answers questions about orders, finds policy rules, and checks refund eligibility. Try the demo and inspect the decisions and evaluation evidence.",
};

const FINDINGS = [
  {
    title: "Safe SQL can still give the wrong answer",
    description: "The query passed its safety checks, but counted order lines instead of units. I compared the results with independent calculations and clarified the metric instructions. Seven questions improved from 14/21 to 21/21 correct outcomes across three runs. Those tests used the direct SQL path; a later Ask check exposed a separate prompt that needed the same fix.",
    href: "/evaluation-lab#findings-finding-2-sql-calculation-errors",
    link: "Read the SQL investigation →",
  },
  {
    title: "A local retrieval result didn't hold up in production",
    description: "Changing embedding models pushed the relevant policy passage outside the retrieval cutoff. Separate thresholds helped other queries, but the specific damaged-shipment query remained unresolved. I kept the failure in the report rather than treating local results as proof that production worked.",
    href: "/evaluation-lab#findings-finding-5-differences-in-the-deployed-environment",
    link: "Read the retrieval investigation →",
  },
  {
    title: "The model interprets the request; code applies the rules",
    description: "Claude extracts intent and proposes tools. Code controls database access and applies the refund rules. The model has no path to issue a refund. The demo also includes an embedded instruction that tries to override the customer's reason, so you can inspect how that request was handled.",
    href: "/scenarios#injection-attempt",
    link: "Inspect the override attempt →",
  },
];

export default function HomePage() {
  const results = getEvalResults();
  const scenario = SCENARIOS.find((item) => item.id === "refund-approval")!;
  const snapshot = getScenarioSnapshot(scenario) as RefundEvaluateResponse;
  const capturedDate = new Date(SNAPSHOT_CAPTURED_AT).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric", timeZone: "UTC",
  });

  return (
    <div className="flex flex-col gap-14">
      <section className="grid items-start gap-8 lg:grid-cols-2 lg:gap-10" aria-labelledby="project-intro">
        <div className="flex flex-col gap-5">
          <p className="text-sm text-gray-500 dark:text-gray-400">E-commerce operations · AI engineering case study</p>
          <h1 id="project-intro" className="text-3xl leading-tight font-semibold sm:text-5xl">
            An AI assistant for <span className="whitespace-nowrap">e-commerce</span> operations
          </h1>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            A support or operations team needs answers from both order records and policy
            documents. This agent lets them ask about refund rates, look up return rules, or
            check whether a customer’s refund request qualifies, in one place.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button asChild><Link href="/scenarios#refund-approval">Try this request live →</Link></Button>
            <Button asChild variant="outline"><Link href="/evaluation-lab">See results &amp; evidence →</Link></Button>
          </div>
          <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">
            A working demo with sample orders and policies. It evaluates refund eligibility;
            it doesn’t issue refunds.
          </p>
        </div>

        <div className="flex flex-col gap-4 rounded-lg border border-black/10 bg-black/[0.02] p-5 sm:p-6 dark:border-white/10 dark:bg-white/[0.02]" aria-labelledby="example-request">
          <h2 id="example-request" className="text-lg font-semibold">One request, from message to decision</h2>
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Customer request</p>
            <blockquote className="mt-2 text-sm leading-relaxed">“{scenario.input}”</blockquote>
          </div>
          <div className="border-t border-black/10 pt-4 dark:border-white/10">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Recorded result</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge variant="success">{snapshot.status.replaceAll("_", " ")}</Badge>
              <span className="text-sm">Eligible under rule {snapshot.rule_applied}: shipping damage.</span>
            </div>
            <p className="mt-3 text-sm text-gray-600 dark:text-gray-300">
              The agent matched the customer and mug to an order, then code checked the refund
              rules. The message says photos are attached; the agent doesn’t inspect the photos.
            </p>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Saved demo response · {capturedDate} · sample data, not a live result.
          </p>
          <Link href="/scenarios#refund-approval" className="self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline">
            See the full response or run it again →
          </Link>
        </div>
      </section>

      <section className="flex flex-col gap-6" aria-labelledby="engineering-findings">
        <div className="flex flex-col gap-3">
          <h2 id="engineering-findings" className="text-2xl font-semibold">Getting an answer is only the first part</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            I built this to work through what happens when a model sits in front of business data
            and rules. Can it calculate the right number? Find the right policy? Stay within what
            it’s allowed to do? Testing exposed gaps that a convincing demo answer didn’t.
          </p>
        </div>
        <div className="rounded-lg border border-black/10 p-5 dark:border-white/10">
          <p className="text-lg font-semibold">Saved evaluation run: {results.overall.passed}/{results.overall.total} tests passed ({results.overall.pass_rate.toFixed(1)}%)</p>
          <p className="mt-2 max-w-prose text-sm text-gray-500 dark:text-gray-400">
            August 22, 2026 local run · {results.overall.failed} failures. This measures the cases
            tested then, not the current deployment. The report includes category results,
            skipped cases, and measurement limits.
          </p>
          <Link href="/evaluation-lab#coverage" className="mt-3 inline-block text-sm font-medium text-accent underline underline-offset-2 hover:no-underline">
            Check the results and their scope →
          </Link>
        </div>
        {FINDINGS.map((finding) => (
          <Card key={finding.title} className="gap-3 p-5 sm:p-6">
            <h3 className="text-lg font-semibold">{finding.title}</h3>
            <p className="max-w-prose text-sm leading-relaxed text-gray-600 dark:text-gray-300">{finding.description}</p>
            <Link href={finding.href} className="self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline">
              {finding.link}
            </Link>
          </Card>
        ))}
      </section>

      <section className="flex flex-col gap-4 border-t border-black/10 pt-8 dark:border-white/10" aria-labelledby="keep-exploring">
        <h2 id="keep-exploring" className="text-xl font-semibold">Follow a request through the system</h2>
        <p className="max-w-prose text-sm text-gray-600 dark:text-gray-300">
          I chose e-commerce because the business questions are familiar, but the answers still
          depend on real calculations, policy rules, and access boundaries. You can try another
          question, inspect its trace, or read why I put each check where it is.
        </p>
        <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-accent [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:no-underline">
          <Link href="/ask">Ask your own question →</Link>
          <Link href="/activity">Inspect request traces →</Link>
          <Link href="/architecture">Read the architecture →</Link>
          <a href={GITHUB_REPO_URL} target="_blank" rel="noopener noreferrer">View the code →</a>
        </div>
      </section>
    </div>
  );
}
