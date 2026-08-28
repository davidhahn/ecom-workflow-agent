"use client";

import { usePathname } from "next/navigation";
import { GITHUB_REPO_URL } from "@/lib/site";

// No case-study URL provided yet. Per instructions, the "Read the case
// study" link is omitted entirely (not rendered pointing at a placeholder)
// until a real URL exists. Set this to bring the link back.
const CASE_STUDY_URL: string | null = null;

export function IntroBanner() {
  const pathname = usePathname();
  // The landing page already tells this story itself, at more length.
  if (pathname === "/") return null;

  return (
    <div className="border-b border-black/10 bg-black/[0.03] px-6 py-3 text-xs text-gray-600 dark:border-white/10 dark:bg-white/[0.03] dark:text-gray-400">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-1">
        <span>
          A demo AI ops agent for an eCommerce business. Ask a question or evaluate a refund, then
          see the full decision trace behind it.
        </span>
        <a
          href={GITHUB_REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-accent underline underline-offset-2 hover:no-underline"
        >
          View on GitHub
        </a>
        {CASE_STUDY_URL && (
          <a
            href={CASE_STUDY_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium underline underline-offset-2 hover:no-underline"
          >
            Read the case study
          </a>
        )}
      </div>
    </div>
  );
}
