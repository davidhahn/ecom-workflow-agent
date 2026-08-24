import type { NextConfig } from "next";
import path from "node:path";

// /api/:path* proxying to the FastAPI backend lives in src/middleware.ts.
// A declarative rewrite here can't inject the X-Internal-Proxy-Secret
// header the backend requires on every request (see app/proxy_secret.py),
// so Edge Middleware does it. The file must sit inside src/: with a src
// directory, Turbopack dev only discovers middleware there. next build
// also accepts the app root, which is how a root-level file deployed fine
// while next dev quietly ran without any proxy.
const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname, "..", ".."),
  },
};

export default nextConfig;
