"use client";

import { motion, useReducedMotion, type Transition } from "motion/react";
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

// Same spring feel as ui/tabs.tsx (sourced from beUI), reused here for the
// active-link underline. Not a beUI file pull: there's no separate beUI nav
// component, this reapplies its layoutId indicator technique to real page
// navigation instead of client-side tab state. It works because NavHeader
// lives in the root layout and stays mounted across route changes, so a
// stable layoutId can animate the bar sliding to the new active link
// instead of just popping there.
const INDICATOR_LAYOUT_ID = "nav-active-indicator";
const INDICATOR_TRANSITION: Transition = {
  type: "spring",
  stiffness: 170,
  damping: 24,
  mass: 1.2,
};

export function NavHeader() {
  const pathname = usePathname();
  const reduce = useReducedMotion();

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
                    ? "relative font-medium text-accent"
                    : "relative text-gray-500 hover:text-accent dark:text-gray-400"
                }
              >
                {tab.label}
                {active && (
                  <motion.span
                    layoutId={INDICATOR_LAYOUT_ID}
                    layout="position"
                    transition={reduce ? { duration: 0 } : INDICATOR_TRANSITION}
                    className="absolute right-0 -bottom-1 left-0 h-0.5 bg-accent"
                  />
                )}
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
