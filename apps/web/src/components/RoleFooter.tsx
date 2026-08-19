"use client";

import { DEMO_ROLES, useRole } from "@/lib/role-context";

const ROLE_LABELS: Record<string, string> = {
  read_only_viewer: "Read-only viewer",
  support_agent: "Support agent",
  manager: "Manager",
  admin: "Admin",
};

// Demoted out of the primary header (see NavHeader) — this is supporting
// technical context (which permission tier the demo calls run as), not the
// first thing a cold viewer should see.
export function RoleFooter() {
  const { role, setRole } = useRole();

  return (
    <footer className="border-t border-black/10 dark:border-white/10">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2 px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
        <label htmlFor="demo-role">Demo role (controls which tools the agent may call)</label>
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
    </footer>
  );
}
