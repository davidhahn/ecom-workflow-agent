"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { DEMO_ROLES, useRole } from "@/lib/role-context";

const TABS = [
  { href: "/", label: "Ask" },
  { href: "/refunds", label: "Refunds" },
  { href: "/activity", label: "Activity" },
];

const ROLE_LABELS: Record<string, string> = {
  read_only_viewer: "Read-only viewer",
  support_agent: "Support agent",
  manager: "Manager",
  admin: "Admin",
};

export function NavHeader() {
  const pathname = usePathname();
  const { role, setRole } = useRole();

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
        <div className="ml-auto flex items-center gap-2">
          <label htmlFor="demo-role" className="text-xs text-gray-500 dark:text-gray-400">
            Role
          </label>
          <select
            id="demo-role"
            value={role}
            onChange={(e) => setRole(e.target.value as typeof role)}
            className="rounded-md border border-black/15 bg-transparent px-2 py-1 text-xs outline-none dark:border-white/15"
          >
            {DEMO_ROLES.map((r) => (
              <option key={r} value={r} className="text-black">
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}
