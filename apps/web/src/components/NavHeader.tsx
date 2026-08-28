"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { GITHUB_REPO_URL } from "@/lib/site";

const TABS = [
  { href: "/scenarios", label: "Scenarios" },
  { href: "/ask", label: "Ask" },
  { href: "/activity", label: "Activity" },
  { href: "/evaluation-lab", label: "Evaluation Lab" },
  { href: "/architecture", label: "Architecture" },
];

export function NavHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-black/10 bg-background/85 backdrop-blur dark:border-white/10">
      <div className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4">
        <Link href="/" className="shrink-0 font-semibold">
          Ops Intelligence Agent
        </Link>
        <nav className="flex min-w-0 flex-1 gap-4 overflow-x-auto whitespace-nowrap">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={
                  active
                    ? "font-medium text-accent underline underline-offset-4"
                    : "text-gray-500 hover:text-accent dark:text-gray-400"
                }
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
        <a
          href={GITHUB_REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-xs text-gray-500 hover:text-accent dark:text-gray-400"
        >
          GitHub
        </a>
      </div>
    </header>
  );
}
