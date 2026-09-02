import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RoleProvider } from "@/lib/role-context";
import { IntroBanner } from "@/components/IntroBanner";
import AskPage from "@/app/ask/page";
import ScenariosPage from "@/app/scenarios/page";

// Both pages call app/lib/api at module scope; mocked here purely so
// rendering them doesn't attempt a real network request, not because
// these tests exercise submit behavior (see ask/page.test.tsx for that).
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, analyzeQuestion: vi.fn(), evaluateRefund: vi.fn() };
});

// IntroBanner reads the route to decide whether to render itself at all
// (it hides on the landing page). Set this before each render.
let mockPathname = "/ask";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

const BANNER_TEXT = /an ai systems engineering case study, using e-commerce ops as the testbed/i;

// This is what layout.tsx composes around {children} for every route,
// reproduced here (mounting the real RootLayout is awkward under RTL's
// container, since its root JSX is <html>/<body>) so the test proves the
// banner sits *outside* and alongside distinct page content, not baked
// into any one page.
function renderRoute(page: React.ReactNode) {
  return render(
    <RoleProvider>
      <IntroBanner />
      {page}
    </RoleProvider>
  );
}

describe("IntroBanner renders app-level, not page-local", () => {
  it("renders on the Ask route, alongside Ask-page-specific content", () => {
    mockPathname = "/ask";
    renderRoute(<AskPage />);

    expect(screen.getByText(BANNER_TEXT)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ask" })).toBeInTheDocument();
  });

  it("renders on the Scenarios route, alongside Scenarios-page-specific content", () => {
    mockPathname = "/scenarios";
    renderRoute(<ScenariosPage />);

    expect(screen.getByText(BANNER_TEXT)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Scenarios" })).toBeInTheDocument();
  });

  it("renders nothing on the landing route, which tells the same story itself", () => {
    mockPathname = "/";
    const { container } = render(<IntroBanner />);

    expect(container).toBeEmptyDOMElement();
  });

  it("includes a GitHub link", () => {
    mockPathname = "/ask";
    render(<IntroBanner />);

    expect(screen.getByRole("link", { name: "View on GitHub" })).toBeInTheDocument();
  });

  it("omits the case-study link when no case-study URL is configured", () => {
    mockPathname = "/ask";
    render(<IntroBanner />);

    expect(screen.queryByRole("link", { name: /case study/i })).not.toBeInTheDocument();
  });
});
