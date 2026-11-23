"use client";

import { useEffect, type MouseEvent, type ReactNode } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useHashTarget } from "@/lib/use-hash-target";

type Step = { id: string; label: string; title: string; content: ReactNode };

export function GuidedDemo({ steps }: { steps: Step[] }) {
  const targetId = useHashTarget();
  const index = Math.max(0, steps.findIndex((step) => step.id === targetId));
  const selected = steps[index];

  function selectStep(event: MouseEvent<HTMLAnchorElement>, id: string) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (window.location.hash === `#${id}`) return;
    window.history.pushState(null, "", `#${id}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }

  useEffect(() => {
    if (targetId === selected.id) {
      const section = document.getElementById(selected.id);
      section?.focus({ preventScroll: true });
    }
  }, [targetId, selected.id]);

  return (
    <div className="flex flex-col gap-8">
      <nav aria-label="Guided demo steps" className="flex flex-wrap gap-2">
        {steps.map((step, i) => (
          <a
            key={step.id}
            href={`#${step.id}`}
            onClick={(event) => selectStep(event, step.id)}
            aria-current={index === i ? "step" : undefined}
            className="rounded-md border border-black/15 px-3 py-2 text-sm hover:bg-black/[0.03] aria-[current=step]:border-accent aria-[current=step]:text-accent dark:border-white/15 dark:hover:bg-white/[0.03]"
          >
            {i + 1}. {step.label}
          </a>
        ))}
      </nav>
      <p className="text-sm text-gray-500 dark:text-gray-400" aria-live="polite">
        Step {index + 1} of {steps.length}
      </p>
      {steps.map((step) => (
        <section
          key={step.id}
          id={step.id}
          hidden={selected.id !== step.id}
          tabIndex={-1}
          aria-labelledby={`${step.id}-heading`}
          className="scroll-mt-24 outline-none"
        >
          <h2 id={`${step.id}-heading`} className="mb-6 text-2xl font-semibold">{step.title}</h2>
          <div className="flex flex-col gap-8">{step.content}</div>
        </section>
      ))}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-black/10 pt-5 dark:border-white/10">
        {index > 0 ? (
          <Button asChild variant="outline"><a href={`#${steps[index - 1].id}`} onClick={(event) => selectStep(event, steps[index - 1].id)}>← Back: {steps[index - 1].label}</a></Button>
        ) : <Link href="/" className="text-sm text-gray-500 underline underline-offset-2">Back to the overview</Link>}
        {index < steps.length - 1 ? (
          <Button asChild><a href={`#${steps[index + 1].id}`} onClick={(event) => selectStep(event, steps[index + 1].id)}>Next: {steps[index + 1].label} →</a></Button>
        ) : <Button asChild><Link href="/ask">Try your own question →</Link></Button>}
      </div>
    </div>
  );
}
