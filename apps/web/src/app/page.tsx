import type { Metadata } from "next";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { SnapshotTabs } from "@/components/SnapshotTabs";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { GITHUB_REPO_URL } from "@/lib/site";
import { RESPONSIBILITY_ROWS } from "@/lib/architecture";
import { getEvalResults } from "@/lib/evals";

export const metadata: Metadata = {
  description:
    "A full-stack case study in reliable AI systems: grounding, deterministic guardrails, evals, and cost and latency tracking, worked out through a real e-commerce ops agent.",
};

const FINDINGS = [
  {
    title: "Safe SQL can still return the wrong business answer",
    problem: "Structural checks passed, but the queries could still calculate the wrong refund rate.",
    decision: "I checked the returned values against independent calculations, then clarified the metric instructions and added result assertions.",
    evidence: "Seven cases improved from 14/21 correct results to 21/21 across three runs. That demonstrates the fix on this workload, not every possible query.",
    href: "/evaluation-lab#findings",
    link: "Read the SQL investigation →",
  },
  {
    title: "A retrieval setting didn't transfer to production",
    problem: "The same policy query ranked the relevant chunk second with one embedding model and fourth with production's model, beyond the cutoff.",
    decision: "I calibrated the retrieval threshold per provider rather than assuming the same settings would work for both.",
    evidence: "Separate thresholds addressed other retrieval failures, but this specific damaged-shipment query remained unresolved. The ranking comparison explains the remaining gap.",
    href: "/evaluation-lab#findings",
    link: "Read the retrieval investigation →",
  },
  {
    title: "The model proposes; code decides what can happen",
    problem: "Interpreting a request requires flexibility. Database permissions and refund eligibility need consistent enforcement.",
    decision: "Claude selects tools and extracts intent. Code validates SQL access and applies fixed refund rules, without giving the model a refund write path.",
    evidence: "The scenario above shows an embedded override being ignored. The architecture and request traces expose the checks behind the decision; one example alone isn't a security guarantee.",
    href: "/architecture",
    link: "Explore the controls and tradeoffs →",
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

  return (
    <div className="flex flex-col gap-14">
      <section className="flex flex-col gap-5">
        <p className="max-w-prose text-lg text-gray-500 dark:text-gray-400">
          AI Systems Engineering Case Study
        </p>
        <h1 className="text-4xl leading-tight font-semibold sm:text-5xl">
          Building an AI agent you can inspect and control
        </h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          An LLM can read a messy business question and decide on its own which tool to use.
          Turning that into something you can rely on is a different problem, closer to systems
          engineering than to prompting. Ops Intelligence Agent is where I worked through it,
          using a full-stack e-commerce ops agent as the testbed.
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

      <section className="flex flex-col gap-6" aria-labelledby="engineering-findings">
        <h2 id="engineering-findings" className="text-2xl font-semibold">
          Three engineering decisions behind the demo
        </h2>
        {FINDINGS.map((finding) => (
          <Card key={finding.title} className="gap-4 p-5 sm:p-6">
            <h3 className="text-lg font-semibold">{finding.title}</h3>
            <dl className="grid gap-3 text-sm text-gray-600 dark:text-gray-300">
              <div>
                <dt className="font-medium text-gray-900 dark:text-gray-100">Problem</dt>
                <dd className="mt-1 max-w-prose">{finding.problem}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-900 dark:text-gray-100">Decision</dt>
                <dd className="mt-1 max-w-prose">{finding.decision}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-900 dark:text-gray-100">Evidence</dt>
                <dd className="mt-1 max-w-prose">{finding.evidence}</dd>
              </div>
            </dl>
            <Link
              href={finding.href}
              className="self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
            >
              {finding.link}
            </Link>
          </Card>
        ))}
      </section>

      <section className="flex flex-col gap-3 border-t border-black/10 pt-10 dark:border-white/10">
        <h2 className="text-lg font-semibold">Why e-commerce</h2>
        <p className="max-w-prose text-sm text-gray-600 dark:text-gray-300">
          E-commerce ops is a familiar domain. Everyone already knows roughly what an order or a
          refund is. The domain itself doesn&apos;t get in the way of the real engineering
          questions. It still comes with a real policy to follow and a real permission boundary
          that has to hold. The same patterns show up anywhere an LLM sits in front of real data
          and real consequences, an internal copilot or a support agent, say. E-commerce just
          happened to be the one I could build end to end without waiting on anyone else&apos;s
          system.
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
