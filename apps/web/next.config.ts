import type { NextConfig } from "next";
import path from "node:path";

// /api/:path* proxying to the FastAPI backend moved to middleware.ts —
// a declarative rewrite here can't inject the X-Internal-Proxy-Secret
// header the backend now requires on every request (see
// app/proxy_secret.py), so Edge Middleware replaces it.
const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname, "..", ".."),
  },
};

export default nextConfig;
