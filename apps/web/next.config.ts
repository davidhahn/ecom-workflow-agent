import type { NextConfig } from "next";
import path from "node:path";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname, "..", ".."),
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
};

export default nextConfig;
