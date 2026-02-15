import type { NextConfig } from "next";

const deployMode = process.env.DEPLOY_MODE || "saas";

const nextConfig: NextConfig = {
  // SaaS mode: standard SSR
  // Private mode: static export for on-premise deployment
  ...(deployMode === "private" ? { output: "export" } : {}),
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
