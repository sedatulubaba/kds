import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  async rewrites() {
    // Vercel Services routes /api directly to FastAPI at the project root.
    if (process.env.VERCEL) return [];
    const backend = process.env.EVCSDS_BACKEND_URL || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  experimental: { proxyTimeout: 200000, proxyClientMaxBodySize: "52mb" },
};

export default nextConfig;
