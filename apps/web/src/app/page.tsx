import type { Metadata } from "next";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { ExpandableImage } from "@/components/ExpandableImage";
import { SnapshotTabs } from "@/components/SnapshotTabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { GITHUB_REPO_URL } from "@/lib/site";
import { RESPONSIBILITY_ROWS } from "@/lib/architecture";
import { getEvalResults, type EvalCategoryResult } from "@/lib/evals";

export const metadata: Metadata = {
  description:
    "A full-stack AI engineering case study exploring RAG, tool orchestration, evals, deterministic guardrails, permissions, observability, latency, and cost through a working e-commerce agent.",
};

// A curated subset, not the full category list. These four map to the
// site's three core capabilities (SQL, RAG, refunds) plus the permission
// gate. The numbers still come from the committed run either way.
const HIGHLIGHT_CATEGORIES = ["sql_semantic", "rag", "refund_evaluator", "permission"];

// Two of the five findings in evals/findings.md, picked to show the site
// measures real gaps and closes them, not just a pass rate. Both link into
// the Evaluation Lab's Findings report.
const FINDING_CARDS: { title: string; body: string }[] = [
  {
    title: "Safe SQL, wrong number.",
    body: "Structural checks passed 21 of 21. The actual values only matched by hand-checking 14 of 21. A prompt fix closed that gap, and it held for three runs after.",
  },
  {
    title: "The same query, two different answers.",
    body: "One embedding model ranked the right policy chunk second. Production's model ranked it fourth, past the cutoff. The threshold now gets calibrated per provider.",
  },
];

const EXPLORE_LINKS: { href: string; label: string; description: string }[] = [
  {
    href: "/scenarios",
    label: "Scenarios",
    description: "Pick a scenario, run it, and see if it does what it's supposed to.",
  },
  {
    href: "/ask",
    label: "Ask",
    description: "Ask your own question about the data or the policy. Claude picks which one it needs.",
  },
  {
    href: "/activity",
    label: "System Traces",
    description: "A running log of every request, with what it cost and what it triggered.",
  },
  {
    href: "/evaluation-lab",
    label: "Evaluation Lab",
    description: "The actual eval numbers, and where each one comes from.",
  },
  {
    href: "/architecture",
    label: "Architecture",
    description: "Where the model's judgment ends and the code takes over, and why.",
  },
];

export default function HomePage() {
  const results = getEvalResults();
  const highlights = HIGHLIGHT_CATEGORIES.map((name) =>
    results.categories.find((c) => c.category === name)
  ).filter((c): c is EvalCategoryResult => c !== undefined);
  const failing = results.categories.filter((c) => c.failed > 0);

  return (
    <div className="flex flex-col gap-14">
      <section className="flex flex-col gap-5">
        <p className="max-w-prose text-lg text-gray-500 dark:text-gray-400">
          AI Systems Engineering Case Study
        </p>
        <h1 className="text-4xl leading-tight font-semibold sm:text-5xl">
          Building an AI agent you can inspect, evaluate, and control
        </h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          LLMs can reason over messy business questions and choose tools dynamically. Turning that
          into something dependable raises different problems: grounding answers in real data,
          controlling what the model can do, measuring unpredictable behavior, handling failures,
          and tracking the cost and latency of every request. Ops Intelligence Agent is a
          full-stack e-commerce ops agent built as a working environment for exploring those
          problems.
        </p>

        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">Data analysis</Badge>
          <Badge variant="secondary">Policy lookup</Badge>
          <Badge variant="secondary">Refund decisions</Badge>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button asChild>
            <Link href="/scenarios">Run a live scenario →</Link>
          </Button>
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
          >
            View on GitHub
          </a>
        </div>

        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/evaluation-lab"
            className="rounded-md border border-black/10 px-4 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
          >
            <span className="font-semibold text-accent">
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
            <span className="font-semibold text-accent">{RESPONSIBILITY_ROWS.length}</span>{" "}
            <span className="text-gray-500 dark:text-gray-400">checks that run without the model</span>
          </Link>
          <Link
            href="/activity"
            className="rounded-md border border-black/10 px-4 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
          >
            <span className="font-semibold text-accent">Every request</span>{" "}
            <span className="text-gray-500 dark:text-gray-400">traced end to end</span>
          </Link>
        </div>
      </section>

      <SnapshotTabs />

      {/* 1. Can we trust the answer? */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">1. Can we trust the answer?</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            An LLM can state something confidently that isn&apos;t true. In an ops setting, an
            answer that cites a policy nobody retrieved, or a number nobody checked, is a
            liability, not a feature.
          </p>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Retrieval compares the question against the policy corpus by similarity and drops
            anything that doesn&apos;t clear a calibrated relevance threshold, so an off-topic
            question gets &quot;I don&apos;t know&quot; instead of a confident guess. A separate
            groundedness check then confirms that any policy rule the final answer cites actually
            appeared among what got retrieved for that request.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {FINDING_CARDS.filter((c) => c.title.startsWith("The same query")).map((card) => (
            <Card key={card.title} className="overflow-hidden p-0">
              <Link
                href="/evaluation-lab#findings"
                className="block p-5 hover:bg-black/[0.03] dark:hover:bg-white/[0.03]"
              >
                <h3 className="font-semibold">{card.title}</h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{card.body}</p>
              </Link>
            </Card>
          ))}
          <Link
            href="/ask"
            className="flex flex-col justify-center rounded-md border border-black/10 p-5 hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
          >
            <h3 className="font-semibold">Try it against a real question</h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              Ask a policy question on the Ask page and see the retrieved evidence and grounding
              status behind the answer.
            </p>
          </Link>
        </div>

        <p className="text-xs text-gray-500 dark:text-gray-400">
          Demonstrates: retrieval-augmented generation, relevance thresholding, groundedness
          verification, uncertainty handling.
        </p>
      </section>

      {/* 2. Can we trust the action? */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">2. Can we trust the action?</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Reasoning well is one problem. Being allowed to act on that reasoning is another. A
            tool-calling agent that can also execute is only as safe as the boundary between
            proposing and doing.
          </p>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Claude proposes what to do next, a SQL query, a tool call, a refund decision. Nothing
            takes effect until deterministic code checks it: an AST-level allowlist restricts
            tables, columns, and functions, a cost gate rejects an expensive query before it runs,
            and a permission gate checks the calling role against every tool. A restricted
            database role backstops all of it, so a bug upstream still can&apos;t reach data the
            role itself doesn&apos;t allow.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Card className="py-5">
            <CardContent className="px-5">
              <p className="font-mono text-xs text-gray-400 dark:text-gray-500">Model</p>
              <h3 className="mt-1 font-semibold">Proposes</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                Claude reads the request and figures out whether the answer needs a SQL query, a
                policy lookup, or both, and drafts one. It never touches the database or the
                refunds table directly.
              </p>
            </CardContent>
          </Card>
          <Card className="py-5">
            <CardContent className="px-5">
              <p className="font-mono text-xs text-gray-400 dark:text-gray-500">Code</p>
              <h3 className="mt-1 font-semibold">Enforces</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                A handful of independent checks run before anything touches real data. Refunds
                follow their own fixed rule waterfall, model or no model, with no write path the
                LLM controls.
              </p>
            </CardContent>
          </Card>
        </div>

        <ExpandableImage
          src="/architecture-diagram.svg"
          alt="Request flow: user request through the agent/orchestrator loop, into the SQL tool or the Policy/RAG tool, through a deterministic enforcement seam, to a final response, with a trace log recording every stage."
          className="mx-auto w-full max-w-2xl rounded-md border border-black/10 dark:border-white/10"
        />

        <p className="text-xs text-gray-500 dark:text-gray-400">
          Demonstrates: deterministic execution, SQL AST validation, permission gating, and an
          authorization boundary independent of the model.
        </p>
      </section>

      {/* 3. How do we know it works? */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">3. How do we know it works?</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Behavior that isn&apos;t measured is a story about the system, not evidence for it.
            A change can look like an improvement in a transcript and still be a regression
            somewhere the transcript doesn&apos;t show.
          </p>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Every claim here comes from a versioned, {results.overall.total}-case eval suite,
            scored deterministically wherever possible and by a judge model only where the
            criterion is genuinely semantic. Every change runs through the same harness before it
            ships, and every failure gets traced to a root cause before it&apos;s counted.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {highlights.map((c) => (
            <Card key={c.category} className="py-4">
              <CardContent className="px-4">
                <p className="font-mono text-xs text-gray-500 dark:text-gray-400">{c.category}</p>
                <p className="mt-1 text-2xl font-semibold text-accent">
                  {c.passed}/{c.n}
                </p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {c.pass_rate.toFixed(1)}%
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {FINDING_CARDS.filter((c) => c.title.startsWith("Safe SQL")).map((card) => (
            <Card key={card.title} className="overflow-hidden p-0">
              <Link
                href="/evaluation-lab#findings"
                className="block p-5 hover:bg-black/[0.03] dark:hover:bg-white/[0.03]"
              >
                <h3 className="font-semibold">{card.title}</h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{card.body}</p>
              </Link>
            </Card>
          ))}
        </div>

        {failing.length > 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Still not at 100%: {failing.map((c) => c.category).join(", ")}.
          </p>
        )}

        <p className="text-xs text-gray-500 dark:text-gray-400">
          Demonstrates: eval-driven development, regression testing, root-cause failure analysis.
        </p>

        <Link
          href="/evaluation-lab"
          className="self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
        >
          See the full breakdown →
        </Link>
      </section>

      {/* 4. Can we understand what happened? */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">4. Can we understand what happened?</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            An answer&apos;s own wording isn&apos;t proof of what actually happened to produce it.
            Without instrumentation, a production LLM system is a black box you can only debug by
            guessing.
          </p>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Every request writes its own record: which tools ran, what got retrieved, the SQL that
            was generated, whether the answer was grounded, which guardrails fired, latency broken
            down by step, tokens, cost, and whether the response was cached or retried. System
            Traces renders that record directly, so a claim about what happened doesn&apos;t have
            to rely on the answer&apos;s own account of itself.
          </p>
        </div>

        <Link
          href="/activity"
          className="self-start rounded-md border border-black/10 px-4 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
        >
          <span className="font-semibold text-accent">Every request</span>{" "}
          <span className="text-gray-500 dark:text-gray-400">traced end to end →</span>
        </Link>

        <p className="text-xs text-gray-500 dark:text-gray-400">
          Demonstrates: request tracing, latency/token/cost accounting, cache behavior, retry
          handling.
        </p>
      </section>

      {/* 5. How should AI and code split the work? */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">5. How should AI and code split the work?</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Architecture here is a series of decisions about where judgment stays with the model
            and where it moves to code, and each of those calls has a specific failure mode if
            it&apos;s drawn in the wrong place.
          </p>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            The orchestration seam is &quot;LLM proposes, Python enforces.&quot; Claude keeps
            tool selection, SQL drafting, field extraction from free text, and synthesizing an
            answer. Deterministic code keeps permissions, SQL safety, refund policy, and the
            groundedness check, {RESPONSIBILITY_ROWS.length} responsibility pairs in total, each
            one a place the design could plausibly have gone the other way.
          </p>
        </div>

        <Link
          href="/architecture"
          className="self-start rounded-md border border-black/10 px-4 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
        >
          <span className="font-semibold text-accent">{RESPONSIBILITY_ROWS.length}</span>{" "}
          <span className="text-gray-500 dark:text-gray-400">checks that run without the model →</span>
        </Link>

        <p className="text-xs text-gray-500 dark:text-gray-400">
          Demonstrates: orchestration design, explicit LLM/code boundaries, tradeoff
          documentation.
        </p>
      </section>

      {/* 6. Does it work as real software? */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">6. Does it work as real software?</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            A prototype that only works in a notebook, or along a single happy path, doesn&apos;t
            say much about whether a design holds up. The reliability questions above only mean
            something if the surrounding system is real, deployed software.
          </p>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            A Next.js and TypeScript frontend talks to a FastAPI backend over generated,
            type-safe API types. Postgres with pgvector, migrated with Alembic and seeded from a
            re-runnable fixture script, backs both the transactional data and the policy
            retrieval index. External calls carry timeouts and bounded retries, failures return
            structured error states instead of raising, and a deterministic subset of the eval
            suite gates every push in CI before the app deploys.
          </p>
        </div>

        <p className="text-xs text-gray-500 dark:text-gray-400">
          Demonstrates: full-stack delivery, API design, data modeling, CI, and deployment.
        </p>
      </section>

      <section className="flex flex-col gap-3 border-t border-black/10 pt-10 dark:border-white/10">
        <h2 className="text-lg font-semibold">Why e-commerce</h2>
        <p className="max-w-prose text-sm text-gray-600 dark:text-gray-300">
          E-commerce ops is a familiar domain that still surfaces real constraints, orders,
          refunds, policies, permissions, without hiding the harder engineering questions behind
          domain complexity. The same patterns, grounding, deterministic control, evaluation,
          observability, apply just as directly to internal copilots, support agents, financial
          workflows, and enterprise knowledge systems.
        </p>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-xl font-semibold">Explore</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {EXPLORE_LINKS.map((link) => (
            <Card key={link.href} className="overflow-hidden p-0">
              <Link
                href={link.href}
                className="block p-5 hover:bg-black/[0.03] dark:hover:bg-white/[0.03]"
              >
                <h3 className="font-semibold">{link.label}</h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{link.description}</p>
              </Link>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
