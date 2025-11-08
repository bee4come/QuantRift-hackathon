import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'opgg-static.akamaized.net',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 's-lol-web.op.gg',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
