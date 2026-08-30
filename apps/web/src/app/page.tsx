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
    "Claude reads the request and decides what to do next. Separate code checks that decision, checks its claims, and logs the whole thing.",
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
    label: "Activity",
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
          Every model gets something wrong eventually. This is how you&apos;d know.
        </p>
        <h1 className="text-4xl leading-tight font-semibold sm:text-5xl">
          An ops agent that shows its work
        </h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          Claude reads the request and decides what to do next. A separate layer of code checks
          that decision before anything runs. It compares each claim in the answer against what
          actually got retrieved. Then it writes down everything that happened. You can look at
          all of it.
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

      <section className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">How it works</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Claude figures out what to do next. Code checks it before anything runs, no
            exceptions. Every step gets a written record. You can look through it later, whenever
            you want.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Card className="py-5">
            <CardContent className="px-5">
              <p className="font-mono text-xs text-gray-400 dark:text-gray-500">1</p>
              <h3 className="mt-1 font-semibold">Model proposes</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                Claude reads the request. It figures out whether the answer needs a SQL query or a
                policy lookup, and drafts one. The database access and the final decision both
                belong to the code that checks its work.
              </p>
            </CardContent>
          </Card>
          <Card className="py-5">
            <CardContent className="px-5">
              <p className="font-mono text-xs text-gray-400 dark:text-gray-500">2</p>
              <h3 className="mt-1 font-semibold">Code decides</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                A handful of checks run before anything touches real data. One checks the SQL
                against an allowlist. Another caps how expensive a query can get. Refunds follow
                their own fixed set of rules, model or no model.
              </p>
            </CardContent>
          </Card>
          <Card className="py-5">
            <CardContent className="px-5">
              <p className="font-mono text-xs text-gray-400 dark:text-gray-500">3</p>
              <h3 className="mt-1 font-semibold">Everything is logged</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                Every request leaves a paper trail. You can open it up and see exactly what
                happened, step by step, cost included.
              </p>
            </CardContent>
          </Card>
        </div>

        <ExpandableImage
          src="/architecture-diagram.svg"
          alt="Request flow: user request through the agent/orchestrator loop, into the SQL tool or the Policy/RAG tool, through a deterministic enforcement seam, to a final response, with a trace log recording every stage."
          className="mx-auto w-full max-w-2xl rounded-md border border-black/10 dark:border-white/10"
        />

        <Link
          href="/architecture"
          className="self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
        >
          Full breakdown →
        </Link>
      </section>

      <section className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">What the evals actually show</h2>
          <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
            Every claim here comes from one real eval run I can point to.
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
          {FINDING_CARDS.map((card) => (
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

        <Link
          href="/evaluation-lab"
          className="self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
        >
          See the full breakdown →
        </Link>
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
