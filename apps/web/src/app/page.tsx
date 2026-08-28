import type { Metadata } from "next";
import Link from "next/link";
import { Badge } from "@/components/Badge";
import { ExpandableImage } from "@/components/ExpandableImage";
import { InjectionSnapshot } from "@/components/InjectionSnapshot";
import { GITHUB_REPO_URL } from "@/components/IntroBanner";
import { RESPONSIBILITY_ROWS } from "@/lib/architecture";
import { getEvalResults, type EvalCategoryResult } from "@/lib/evals";

export const metadata: Metadata = {
  description:
    "Claude proposes what to do next. Deterministic code decides what actually runs, checks its claims, and logs the whole trail.",
};

// Curated, not the full category list — these four map to the site's three
// core capabilities (SQL, RAG, refunds) plus the permission gate. Numbers
// still come from the committed run, so they can't drift from the choice.
const HIGHLIGHT_CATEGORIES = ["sql_semantic", "rag", "refund_evaluator", "permission"];

const EXPLORE_LINKS: { href: string; label: string; description: string }[] = [
  {
    href: "/scenarios",
    label: "Scenarios",
    description: "Run a curated case and see the result next to the behavior that was promised.",
  },
  {
    href: "/ask",
    label: "Ask",
    description: "Ask your own question, over SQL data and refund policy both.",
  },
  {
    href: "/activity",
    label: "Activity",
    description: "Every request logged: latency, cost, and gate outcomes.",
  },
  {
    href: "/evaluation-lab",
    label: "Evaluation Lab",
    description: "The real eval numbers, and where each one came from.",
  },
  {
    href: "/architecture",
    label: "Architecture",
    description: "What the model decides, what the code decides, and why.",
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
          Every model gets something wrong eventually. This is how you&apos;d know.
        </p>
        <h1 className="text-4xl leading-tight font-semibold sm:text-5xl">
          An ops agent that shows its work
        </h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          Claude reads the request and proposes what to do. Deterministic code decides whether
          that&apos;s allowed, checks its claims against what was retrieved, and logs the whole
          trail so the answer isn&apos;t the only evidence.
        </p>

        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">Data analysis</Badge>
          <Badge tone="neutral">Policy lookup</Badge>
          <Badge tone="neutral">Refund decisions</Badge>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Link
            href="/scenarios"
            className="rounded-md bg-foreground px-5 py-2.5 text-sm font-medium text-background"
          >
            Run a live scenario →
          </Link>
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium underline underline-offset-2 hover:no-underline"
          >
            View on GitHub
          </a>
        </div>

        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/evaluation-lab"
            className="rounded-md border border-black/10 px-4 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
          >
            <span className="font-semibold">
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
            <span className="font-semibold">{RESPONSIBILITY_ROWS.length}</span>{" "}
            <span className="text-gray-500 dark:text-gray-400">
              deterministic checks run independent of the model
            </span>
          </Link>
          <Link
            href="/activity"
            className="rounded-md border border-black/10 px-4 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
          >
            <span className="font-semibold">Every request</span>{" "}
            <span className="text-gray-500 dark:text-gray-400">traced end to end</span>
          </Link>
        </div>
      </section>

      <InjectionSnapshot />

      <section className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">How it works</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Claude proposes. Separate code enforces. Every step gets logged.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-md border border-black/10 p-5 dark:border-white/10">
            <p className="font-mono text-xs text-gray-400 dark:text-gray-500">1</p>
            <h3 className="mt-1 font-semibold">Model proposes</h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              Claude reads the request, drafts SQL, or reads a retrieved policy chunk. It never
              touches the database or writes a decision.
            </p>
          </div>
          <div className="rounded-md border border-black/10 p-5 dark:border-white/10">
            <p className="font-mono text-xs text-gray-400 dark:text-gray-500">2</p>
            <h3 className="mt-1 font-semibold">Code decides</h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              An AST allowlist, a cost gate, a restricted database role, and a fixed refund
              waterfall each run independent of the model.
            </p>
          </div>
          <div className="rounded-md border border-black/10 p-5 dark:border-white/10">
            <p className="font-mono text-xs text-gray-400 dark:text-gray-500">3</p>
            <h3 className="mt-1 font-semibold">Everything is logged</h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              Every request writes its own record: tools called, gates passed, cost, latency, and
              the final answer.
            </p>
          </div>
        </div>

        <ExpandableImage
          src="/architecture-diagram.svg"
          alt="Request flow: user request through the agent/orchestrator loop, into the SQL tool or the Policy/RAG tool, through a deterministic enforcement seam, to a final response, with a trace log recording every stage."
          className="mx-auto w-full max-w-2xl rounded-md border border-black/10 dark:border-white/10"
        />

        <Link
          href="/architecture"
          className="self-start text-sm font-medium underline underline-offset-2 hover:no-underline"
        >
          Full breakdown →
        </Link>
      </section>

      <section className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">Measured, not asserted</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Every claim on this site traces back to one committed eval run.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {highlights.map((c) => (
            <div key={c.category} className="rounded-md border border-black/10 p-4 dark:border-white/10">
              <p className="font-mono text-xs text-gray-500 dark:text-gray-400">{c.category}</p>
              <p className="mt-1 text-2xl font-semibold">
                {c.passed}/{c.n}
              </p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {c.pass_rate.toFixed(1)}%
              </p>
            </div>
          ))}
        </div>

        {failing.length > 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {failing.map((c) => c.category).join(", ")}{" "}
            {failing.length === 1 ? "isn't" : "aren't"} at 100% yet. Every failure is documented,
            not hidden.
          </p>
        )}

        <Link
          href="/evaluation-lab"
          className="self-start text-sm font-medium underline underline-offset-2 hover:no-underline"
        >
          See the full breakdown →
        </Link>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-xl font-semibold">Explore</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {EXPLORE_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md border border-black/10 p-5 hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/[0.03]"
            >
              <h3 className="font-semibold">{link.label}</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{link.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
