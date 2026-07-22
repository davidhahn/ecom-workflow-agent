import { NextResponse, type NextRequest } from "next/server";

// Backend base URL — same variable next.config.ts's rewrite used to read.
// Public because the default (localhost:8000) is dev-only and the deployed
// value isn't secret; what must stay server-side is the header below.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Server-side-only: never prefixed NEXT_PUBLIC_, so it's never bundled into
// client JS. Must match the backend's INTERNAL_PROXY_SECRET exactly (see
// apps/api/app/proxy_secret.py and README.md's Deployment section).
const INTERNAL_PROXY_SECRET = process.env.INTERNAL_PROXY_SECRET;

export function middleware(request: NextRequest) {
  if (!INTERNAL_PROXY_SECRET) {
    throw new Error(
      "INTERNAL_PROXY_SECRET is not set — required to proxy /api requests to the backend."
    );
  }

  // Strip the leading /api the same way next.config.ts's rewrite did
  // ("/api/:path*" -> "${API_URL}/:path*"), so apps/web/src/lib/api.ts's
  // fetch("/api/...") calls reach the same backend routes as before.
  const destination = new URL(
    request.nextUrl.pathname.replace(/^\/api/, ""),
    API_URL
  );
  destination.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  headers.set("X-Internal-Proxy-Secret", INTERNAL_PROXY_SECRET);

  return NextResponse.rewrite(destination, { request: { headers } });
}

export const config = {
  matcher: "/api/:path*",
};
