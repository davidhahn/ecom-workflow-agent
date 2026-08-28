import { ExpandableImage } from "@/components/ExpandableImage";
import { RESPONSIBILITY_ROWS } from "@/lib/architecture";

const NOT_BUILT: { title: string; body: string }[] = [
  {
    title: "Multi-agent decomposition",
    body: "A Planner and a Data Analyst module already exist, tested and working. No endpoint routes a live request through them, because the measured workflow never turned up a problem only a third agent could fix. Every additional agent is more latency, and one more thing that can break.",
  },
  {
    title: "A workflow framework (LangGraph or similar)",
    body: "The orchestration today is one direct call to the Anthropic SDK, with a single bounded retry. It's small enough to read start to finish in one sitting. A framework migration would change the plumbing, and leave every failure the evals have found exactly where it is.",
  },
  {
    title: "A vector database migration, or a reranker",
    body: "The policy corpus holds 21 chunks in Postgres, through pgvector. That's the whole search space. One real retrieval problem turned up during evals, and calibrating the relevance threshold per embedding provider traced it and mostly fixed it.",
  },
  {
    title: "Production OAuth or a full identity system",
    body: "Every request carries a demo role through a header. The docs call it that, plainly, right on the page. Real authentication would prove a skill this project already shows somewhere else.",
  },
  {
    title: "A second agentic investigation workflow",
    body: "The error analysis after the first eval run pointed somewhere else: a write-refusal bug, and eval categories too small to trust yet. Those won, so the Report Writer stage never got built, the piece that would have turned the Planner and Data Analyst's findings into a real answer. Both modules still only run from tests.",
  },
  {
    title: "More UI surface",
    body: "The interface has one job: put real evidence in front of a reader. An admin dashboard or a settings page would turn it into something else, a full operations product, which was never the goal here.",
  },
];

const DECISION_LINKS: { title: string; body: string; entry: string }[] = [
  {
    title: "Why SQL safety runs on four separate layers",
    body: "A mistake that slips past one check has three more chances to get caught.",
    entry: "#5",
  },
  {
    title: "Where the groundedness check still lets a lie through",
    body: "It checks whether a rule number showed up in what got retrieved, and stops there, so a wrong claim attached to a real number slips past clean.",
    entry: "#32",
  },
  {
    title: "A judge grading itself, caught before it ran",
    body: "The judge and the app under test read the same model env var, so swapping the model under test would have swapped the judge too.",
    entry: "#41",
  },
  {
    title: "Haiku was cheaper, and it stayed on the bench",
    body: "It matched Sonnet almost everywhere, and lost the cases that carry the real cost: refund totals, compliance verdicts.",
    entry: "#44",
  },
  {
    title: "The pipeline that works and has nowhere to run",
    body: "Error analysis pointed at bugs in the measured core first, and a third agent lost to that ranking.",
    entry: "#45",
  },
];

const DECISIONS_URL = "https://github.com/davidhahn/ecom-workflow-agent/blob/main/DECISIONS.md";

export default function ArchitecturePage() {
  return (
    <div className="flex flex-col gap-14">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold">Architecture</h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          How decisions split between the model and the code, and why.
        </p>
      </div>

      <section>
        <ExpandableImage
          src="/architecture-diagram.svg"
          alt="Request flow: user request through the agent/orchestrator loop, into the SQL tool or the Policy/RAG tool, through a deterministic enforcement seam, to a final response, with a trace log recording every stage."
          className="mx-auto w-full max-w-4xl rounded-md border border-black/10 dark:border-white/10"
        />
        <p className="mt-2 text-center text-xs text-gray-500 dark:text-gray-400">
          Click to enlarge.
        </p>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold">Responsibility split</h2>
        <p className="mb-5 max-w-prose text-base text-gray-600 dark:text-gray-300">
          One question: what decisions does this system delegate to probabilistic behavior? The
          model handles the parts that need flexibility, like reading free text, writing SQL, and
          interpreting policy language. Every row on the right is a real constraint. It runs
          independently of the model, and it guards one consequential action.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-black/10 text-xs text-gray-500 dark:border-white/10 dark:text-gray-400">
                <th className="py-3 pr-4 font-medium">LLM proposes / interprets</th>
                <th className="py-3 pr-4 font-medium">Deterministic systems enforce</th>
              </tr>
            </thead>
            <tbody>
              {RESPONSIBILITY_ROWS.map((row, i) => (
                <tr key={i} className="border-b border-black/5 align-top dark:border-white/5">
                  <td className="py-3 pr-4">{row.llm}</td>
                  <td className="py-3 pr-4 text-gray-600 dark:text-gray-300">{row.enforced}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold">Deliberately not built</h2>
        <p className="mb-5 max-w-prose text-base text-gray-600 dark:text-gray-300">
          Every one of these is a tool I know how to use. Each one stayed out for a specific
          reason.
        </p>
        <div className="flex flex-col gap-3">
          {NOT_BUILT.map((item) => (
            <details
              key={item.title}
              className="rounded-md border border-black/10 dark:border-white/10"
            >
              <summary className="cursor-pointer select-none px-5 py-3.5 text-sm font-medium">
                {item.title}
              </summary>
              <p className="max-w-prose border-t border-black/10 px-5 py-4 text-sm text-gray-600 dark:border-white/10 dark:text-gray-300">
                {item.body}
              </p>
            </details>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold">Decision links</h2>
        <p className="mb-5 max-w-prose text-base text-gray-600 dark:text-gray-300">
          Five entries from <code>DECISIONS.md</code>, picked for what each one reveals about how
          a call got made.
        </p>
        <dl className="flex flex-col gap-5">
          {DECISION_LINKS.map((item) => (
            <div key={item.entry}>
              <dt className="font-medium">
                <a href={DECISIONS_URL} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                  {item.title}
                </a>{" "}
                <span className="font-mono text-xs text-gray-400 dark:text-gray-500">
                  DECISIONS.md {item.entry}
                </span>
              </dt>
              <dd className="text-sm text-gray-600 dark:text-gray-300">{item.body}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
