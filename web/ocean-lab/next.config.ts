import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    const headers = [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    ];
    return ["/", "/:path*"].map((source) => ({ source, headers }));
  },
};

export default nextConfig;
