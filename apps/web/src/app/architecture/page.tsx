import { ExpandableImage } from "@/components/ExpandableImage";
import { NextSteps } from "@/components/NextSteps";
import { GITHUB_REPO_URL } from "@/lib/site";

const CONTROLS = [
  ["Tool access", "Role checks apply to the SQL, policy retrieval, ticket, and invoice endpoints through a shared permission dependency. Analyze and refund operations are read-only and available to every demo role."],
  ["SQL execution", "Generated queries pass validation and an estimated-cost check, then run through a restricted database role. Postgres enforces that role’s grants independently of application validation."],
  ["Refund evaluation", "Application code resolves the customer and order, then applies fixed policy rules to return a decision."],
  ["After answer generation", "Citation matching checks policy names and numbers against retrieved passages. Topic coverage checks for claims about unsupported subjects. These checks can flag an answer; they do not establish that it applied a policy correctly."],
  ["Request completion", "Logs record outcomes and timing, with token usage and estimated cost where available. Analyze requests also record an ordered tool-call trace."],
];

const FAILURES = [
  ["A query fails validation or exceeds the cost limit", "The query is rejected before execution."],
  ["A covered model call encounters a transient failure", "SQL proposal and analyze calls allow one retry, with a timeout and fixed delay. Other model-call sites remain outside this wrapper."],
  ["Both attempts fail", "The path returns its structured error or incomplete response."],
  ["The tool loop reaches its limit", "Analyze returns an explicit incomplete response."],
  ["A refund request cannot be matched to a customer or product", "The evaluator returns could_not_process."],
  ["Retrieval finds no qualifying passages", "The tool returns no supporting policy evidence."],
  ["An answer cites a policy rule that was not retrieved", "The grounding check flags the answer. The generated answer remains visible."],
];

const LIMITS = [
  {
    title: "Identity and data access",
    body: "Demo roles come from a caller-set header. Real customer use requires verified identity and tenant isolation. Sensitive-column handling currently centers on customers.email; a broader classification policy is still needed.",
  },
  {
    title: "Retrieval and answer checks",
    body: "Retrieval thresholds are calibrated separately for local and production embedding models. One known phrasing still ranks the wrong policy passage first in production. Citation matching checks whether a source was retrieved, but an answer can still misinterpret that source. The checks can also produce false warnings.",
  },
  {
    title: "Investigation workflow",
    body: "A Planner and Data Analyst gather evidence for open-ended questions such as why revenue dropped. They are tested directly, but have no endpoint or final answer-writing stage. I deferred that work while addressing failures in the existing workflows.",
  },
];

const DECISIONS = [
  { title: "SQL access controls", anchor: "5-sql-query-path-four-independent-differently-shaped-safety-layers", body: "Query validation and database permissions constrain execution. Audit logging records the attempt." },
  { title: "Citation-check limitations", anchor: "32-groundedness-heuristic-four-ways-it-gets-fooled", body: "Calibration exposed unsupported claims that passed citation matching and correct answers that triggered warnings." },
  { title: "Model selection", anchor: "44-staying-on-sonnet-and-turning-down-a-workload-split", body: "I retained Sonnet after comparing quality by category and deferred routing selected requests to Haiku." },
  { title: "Investigation workflow deferral", anchor: "45-closing-the-investigation-pipeline-as-a-formal-scope-deferral", body: "Completing the workflow would require a final answer stage and end-to-end evaluation." },
];

const COPY = "max-w-prose text-base text-gray-600 dark:text-gray-300";

export default function ArchitecturePage() {
  return (
    <div className="flex flex-col gap-12">
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold">Architecture</h1>
        <p className={COPY}>
          I designed the system to let Claude interpret requests and choose tools while application
          code controls execution. This page follows a request through those controls and shows
          what happens when something fails.
        </p>
      </header>

      <section aria-label="Architecture diagram">
        <ExpandableImage
          src="/architecture-diagram.svg"
          alt="Architecture diagram showing the agent loop, SQL and policy tools, execution controls, and request logging."
          className="mx-auto w-full max-w-4xl rounded-md border border-black/10 dark:border-white/10"
        />
        <p className="mt-2 text-center text-xs text-gray-500 dark:text-gray-400">Click to enlarge.</p>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">How a request moves through the system</h2>
        <ol className={`${COPY} list-decimal space-y-2 pl-5`}>
          <li>Claude chooses SQL or policy retrieval to gather evidence for the request.</li>
          <li>Application code validates generated SQL before execution.</li>
          <li>Tool results return to Claude, which can request more evidence within a four-round loop.</li>
          <li>The generated answer passes through policy citation and topic-coverage checks.</li>
          <li>The request log records the outcome and execution details.</li>
        </ol>
        <h3 className="text-lg font-medium">Refund requests</h3>
        <p className={COPY}>
          Refund requests follow a separate path. Claude extracts the relevant fields. Application
          code resolves the order and applies the policy rules to return a decision. The evaluator
          does not update the refund record.
        </p>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">Where the controls run</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Controls by request stage</caption>
            <thead><tr className="border-b border-black/10 dark:border-white/10"><th scope="col" className="py-3 pr-4">Stage</th><th scope="col" className="py-3">Control</th></tr></thead>
            <tbody>{CONTROLS.map(([stage, control]) => (
              <tr key={stage} className="border-b border-black/5 align-top dark:border-white/5">
                <th scope="row" className="py-3 pr-4 font-medium">{stage}</th>
                <td className="py-3 text-gray-600 dark:text-gray-300">{control}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">What happens when a request fails</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Failure conditions and responses</caption>
            <thead><tr className="border-b border-black/10 dark:border-white/10"><th scope="col" className="py-3 pr-4">Condition</th><th scope="col" className="py-3">Response</th></tr></thead>
            <tbody>{FAILURES.map(([condition, response]) => (
              <tr key={condition} className="border-b border-black/5 align-top dark:border-white/5">
                <th scope="row" className="py-3 pr-4 font-medium">{condition}</th>
                <td className="py-3 text-gray-600 dark:text-gray-300">{response}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">Deployment and current limits</h2>
        <p className={COPY}>
          Vercel hosts the frontend. Render hosts the API and database, along with the daily reseed
          job. The frontend proxy adds a shared secret that the backend checks. CORS separately
          restricts browser access by origin.
        </p>
        <p className={COPY}>
          Local development uses BAAI/bge-m3 for policy embeddings. Production uses Voyage because
          the local model exceeded the deployment memory budget. That difference affects retrieval
          behavior and needs its own evaluation.
        </p>
        {LIMITS.map(({ title, body }) => (
          <details key={title} className="rounded-md border border-black/10 dark:border-white/10">
            <summary className="cursor-pointer px-5 py-3.5 text-sm font-medium">{title}</summary>
            <p className="max-w-prose border-t border-black/10 px-5 py-4 text-sm text-gray-600 dark:border-white/10 dark:text-gray-300">{body}</p>
          </details>
        ))}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">Implementation and decisions</h2>
        <p className={COPY}>
          The <a className="underline underline-offset-2" href={`${GITHUB_REPO_URL}/blob/main/ARCHITECTURE.md`}>architecture document</a> includes source-file links and further implementation detail.
          These decisions explain the choices behind the controls.
        </p>
        <dl className="flex flex-col gap-5">
          {DECISIONS.map(({ title, anchor, body }) => (
            <div key={anchor}>
              <dt className="font-medium"><a href={`${GITHUB_REPO_URL}/blob/main/DECISIONS.md#${anchor}`} className="underline underline-offset-2">{title}</a></dt>
              <dd className="mt-1 max-w-prose text-sm text-gray-600 dark:text-gray-300">{body}</dd>
            </div>
          ))}
        </dl>
      </section>

      <NextSteps links={[
        { href: "/scenarios", label: "Scenarios", note: "Follow a request and inspect its result." },
        { href: "/evaluation-lab", label: "Evaluation Lab", note: "See the measurements and recorded failures." },
        { href: `${GITHUB_REPO_URL}/blob/main/ARCHITECTURE.md`, label: "Architecture document", note: "Read the implementation details and source references." },
      ]} />
    </div>
  );
}
