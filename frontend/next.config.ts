import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  async rewrites() {
    const backend = process.env.EVCSDS_BACKEND_URL || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  experimental: { proxyTimeout: 200000, proxyClientMaxBodySize: "52mb" },
};

export default nextConfig;
