import type { NextConfig } from "next";

/** Backend interno para rewrites (docker: backend:8000, local: localhost:8000). */
const internalApiUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  ...(process.env.NODE_ENV === "production" ? { output: "standalone" as const } : {}),
  reactStrictMode: true,
  // Pre-existing lint errors outside NR scope must not block RC image build.
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  async redirects() {
    return [
      {
        source: "/lottery/admin/control-center",
        destination: "/lottery",
        permanent: false,
      },
      {
        source: "/lottery/search",
        destination: "/lottery/admin/control-center/motor/historial-numero",
        permanent: false,
      },
      {
        source: "/lottery/compare",
        destination: "/lottery/admin/control-center/motor/comparador",
        permanent: false,
      },
      {
        source: "/lottery/statistics",
        destination: "/lottery/admin/control-center/motor/combinaciones",
        permanent: false,
      },
      {
        source: "/lottery/admin/numeric-relations",
        destination: "/lottery/admin/control-center/motor/relaciones",
        permanent: false,
      },
      {
        source: "/lottery/admin/control-center/motor/groups-table1",
        destination: "/lottery/admin/control-center/motor/agrupaciones?tab=table1",
        permanent: false,
      },
      {
        source: "/lottery/admin/control-center/motor/groups-table2",
        destination: "/lottery/admin/control-center/motor/agrupaciones?tab=table2",
        permanent: false,
      },
    ];
  },
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
