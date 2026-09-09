import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Only use rewrites in development when NEXT_PUBLIC_API_URL is not set
    // In production, NEXT_PUBLIC_API_URL should be set via environment variable
    if (process.env.NODE_ENV === 'development' && !process.env.NEXT_PUBLIC_API_URL) {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.BACKEND_URL || 'http://localhost:8001'}/api/:path*`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
