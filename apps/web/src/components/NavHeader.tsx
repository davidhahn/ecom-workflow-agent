"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "Ask" },
  { href: "/refunds", label: "Refunds" },
  { href: "/activity", label: "Activity" },
];

export function NavHeader() {
  const pathname = usePathname();

  return (
    <header className="border-b border-black/10 dark:border-white/10">
      <div className="mx-auto flex max-w-3xl items-center gap-6 px-4 py-3">
        <span className="font-semibold">Ops Intelligence Agent</span>
        <nav className="flex gap-4">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={
                  active
                    ? "font-medium underline underline-offset-4"
                    : "text-gray-500 hover:text-foreground dark:text-gray-400"
                }
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
