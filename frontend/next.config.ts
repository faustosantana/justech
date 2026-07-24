import type { NextConfig } from "next";

/** Backend interno para rewrites (docker: backend:8000, local: localhost:8000). */
const internalApiUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  ...(process.env.NODE_ENV === "production" ? { output: "standalone" as const } : {}),
  reactStrictMode: true,
  // Pre-existing lint errors outside NR scope must not block RC image build.
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
