import { NextSteps } from "@/components/NextSteps";
import { ScenarioDemo } from "@/components/ScenarioDemo";
import Link from "next/link";

export const metadata = {
  title: "Scenarios",
};

export default function ScenariosPage() {
  return (
    <div className="flex flex-col gap-12">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold">Scenarios</h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          Choose a scenario, compare its request and saved result, then run it fresh to inspect the execution trace.
        </p>
        <Link href="/guided-demo" className="self-start text-sm font-medium text-accent underline underline-offset-2 hover:no-underline">
          New here? Follow the guided demo →
        </Link>
      </div>

      <p className="max-w-prose text-sm text-gray-500 dark:text-gray-400">
        Uses seeded sample data. Refund scenarios evaluate eligibility; they do not issue refunds.
      </p>

      <ScenarioDemo />

      <NextSteps
        links={[
          { href: "/ask", label: "Ask", note: "Ask your own question instead of a curated one." },
          { href: "/activity", label: "System Traces", note: "See every request this demo has logged." },
        ]}
      />
    </div>
  );
}
