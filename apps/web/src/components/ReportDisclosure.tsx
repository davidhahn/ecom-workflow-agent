"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { useHashTarget } from "@/lib/use-hash-target";

export function ReportDisclosure({ id, children }: { id: string; children: ReactNode }) {
  const ref = useRef<HTMLDetailsElement>(null);
  const targetId = useHashTarget();

  useEffect(() => {
    const report = ref.current;
    const target = document.getElementById(targetId);
    if (report && target && (target === report || report.contains(target))) {
      report.open = true;
      target.scrollIntoView?.({ block: "start" });
    }
  }, [targetId]);

  return (
    <details ref={ref} id={id} className="scroll-mt-20 overflow-hidden rounded-md border border-black/10 dark:border-white/10">
      {children}
    </details>
  );
}
