"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

// Must match ROLE_PERMISSIONS in apps/api/app/permissions.py exactly.
export const DEMO_ROLES = ["read_only_viewer", "support_agent", "manager", "admin"] as const;
export type DemoRole = (typeof DEMO_ROLES)[number];

const DEFAULT_ROLE: DemoRole = "read_only_viewer";

type RoleContextValue = {
  role: DemoRole;
  setRole: (role: DemoRole) => void;
};

const RoleContext = createContext<RoleContextValue | null>(null);

// Client-side-only, per-session demo mechanic — no persistence across page
// reloads, no real auth. Resets to DEFAULT_ROLE on every page load.
export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<DemoRole>(DEFAULT_ROLE);
  return <RoleContext.Provider value={{ role, setRole }}>{children}</RoleContext.Provider>;
}

export function useRole(): RoleContextValue {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error("useRole must be used within a RoleProvider");
  return ctx;
}
