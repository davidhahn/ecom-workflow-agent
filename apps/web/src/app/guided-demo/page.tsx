import Link from "next/link";
import { GuidedDemo } from "@/components/GuidedDemo";
import { ScenarioCard } from "@/components/ScenarioCard";
import { getPublicEvalReport, REPORT_RUN } from "@/lib/public-eval-report";
import { SCENARIOS } from "@/lib/scenarios";

export const metadata = {
  title: "Guided demo",
  description: "Follow an e-commerce operations question from request to result, see where code checks the model, and inspect the evaluation evidence.",
};

const linkStyle = "self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline";

function Scenario({ id }: { id: string }) {
  const scenario = SCENARIOS.find((item) => item.id === id);
  if (!scenario) throw new Error(`Missing guided demo scenario: ${id}`);
  return <ScenarioCard scenario={scenario} traceNewTab />;
}

export default function GuidedDemoPage() {
  const report = getPublicEvalReport();
  return (
    <div className="flex flex-col gap-12">
      <header className="flex flex-col gap-3">
        <p className="text-sm text-gray-500 dark:text-gray-400">Start here · Five steps through the product</p>
        <h1 className="text-3xl font-semibold sm:text-4xl">A guided look at the operations agent</h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          See how it answers a data question, finds a policy, and checks a refund request.
          Then look at where it stops and what testing caught. Each step starts with a saved
          result, so you can follow the whole tour without waiting for a model call.
        </p>
        <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">
          This demo uses sample orders and policies. Refund decisions only evaluate eligibility;
          no refund is issued. “Run it fresh” is optional. Its trace opens in a new tab so you
          can keep your place in the tour. Live results can differ from saved examples.
        </p>
      </header>
      <GuidedDemo steps={[
        {
          id: "data", label: "Data question", title: "Start with a question about the orders",
          content: <>
            <p className="max-w-prose">An operations analyst wants to check how often Home products are refunded. The agent needs to calculate this from order records, rather than guess from policy text.</p>
            <div className="rounded-lg border border-black/10 p-5 dark:border-white/10">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Request</p>
              <blockquote className="mt-2 text-lg">{report.example.request}</blockquote>
              <p className="mt-5 text-xs font-medium text-gray-500 dark:text-gray-400">Recorded result</p>
              <p className="mt-2 text-2xl font-semibold">{report.example.refunded} approved refunded units / {report.example.sold} units sold = {report.example.rate.toFixed(2)}%</p>
              <p className="mt-3 max-w-prose text-sm text-gray-500 dark:text-gray-400">August 22, 2026 local evaluation · direct SQL endpoint, prompt v2 · not a live Ask result. This case matched an independently calculated answer.</p>
            </div>
            <p className="max-w-prose text-sm text-gray-600 dark:text-gray-300"><strong>What to notice:</strong> the model proposes a query; code checks whether it can run with read-only access. Those checks don’t prove the math is right. The evaluation separately checks the returned values.</p>
            <Link href="/evaluation-lab#example" className={linkStyle}>Inspect this calculation and its source →</Link>
            <Link href="/ask" className={linkStyle}>Try a data question in Ask →</Link>
          </>,
        },
        {
          id: "policy", label: "Policy lookup", title: "Find the rule before making a decision",
          content: <>
            <p className="max-w-prose">A support agent needs to know what a shipping-damage claim requires. This question calls for a policy lookup, not an order calculation.</p>
            <p className="max-w-prose text-sm text-gray-600 dark:text-gray-300"><strong>What to notice:</strong> the saved answer cites rules 4 and 10 from the retrieved policy. The citation check only checks cited rules against retrieved material; it doesn’t verify every claim. A production retrieval failure is documented in the report.</p>
            <Scenario id="policy-retrieval" />
          </>,
        },
        {
          id: "refund", label: "Refund decision", title: "Apply the policy to a customer’s request",
          content: <>
            <p className="max-w-prose">Now a customer asks for a refund on a mug damaged during shipping. The agent extracts who is asking, which item they mean, and the reason. It matches the order, then code applies the refund rules.</p>
            <p className="max-w-prose text-sm text-gray-600 dark:text-gray-300"><strong>What to notice:</strong> the saved eligibility decision names rule 4. The evidence flag comes from what the message says; the agent doesn’t inspect photos. If you run it fresh, open “View execution trace” to see the recorded result and extracted fields. No payment is made.</p>
            <Scenario id="refund-approval" />
          </>,
        },
        {
          id: "boundary", label: "When it stops", title: "Don’t guess which customer is asking",
          content: <>
            <p className="max-w-prose">This request mentions headphones but gives no customer identity. A plausible-sounding refund decision would be the wrong outcome if the system can’t reliably match the order.</p>
            <p className="max-w-prose text-sm text-gray-600 dark:text-gray-300"><strong>What to notice:</strong> the saved response is “could_not_process.” It stops rather than choosing a customer. This is one boundary example, not proof that every ambiguous or adversarial request is handled correctly.</p>
            <Scenario id="ambiguous-refund-refusal" />
            <Link href="/scenarios#injection-attempt" className={linkStyle}>Also try a message that attempts to override the rules →</Link>
          </>,
        },
        {
          id: "evidence", label: "Test evidence", title: "Check the demo against more than one example",
          content: <>
            <p className="max-w-prose">The examples show the product’s behavior. The evaluation asks whether it holds up across a defined set of questions, and records what failed.</p>
            <div className="rounded-lg border border-black/10 p-5 dark:border-white/10">
              <p className="text-2xl font-semibold">{report.results.overall.passed}/{report.results.overall.total} tests passed</p>
              <p className="mt-2 text-sm">{report.datasetCount} dataset cases · {report.categoryCount} categories · {report.skipped} not run · {report.results.overall.failed} failures</p>
              <p className="mt-3 max-w-prose text-sm text-gray-500 dark:text-gray-400">Saved August 22, 2026 local run ({REPORT_RUN}). These results describe the cases and configuration tested then, not the current deployment.</p>
            </div>
            <p className="max-w-prose text-sm text-gray-600 dark:text-gray-300"><strong>One failure it caught:</strong> safe SQL counted order lines instead of units, producing the wrong refund rate. The seven SQL questions improved from {report.regression[0].passed}/{report.regression[0].n} to {report.regression[1].passed}/{report.regression[1].n} correct outcomes across three runs after several configuration changes. That comparison used the direct SQL path. Ask later needed the same metric instructions added to its separate prompt.</p>
            <p className="max-w-prose">You’ve now seen a data answer, a policy lookup, an eligibility decision, and a refusal. To go deeper, inspect a request’s trace or read the results and the remaining limitations.</p>
            <Link href="/evaluation-lab" className={linkStyle}>Read the full results and measurement limits →</Link>
            <Link href="/activity" className={linkStyle}>Explore the request traces →</Link>
            <Link href="/architecture" className={linkStyle}>See where the model ends and code takes over →</Link>
          </>,
        },
      ]} />
    </div>
  );
}
