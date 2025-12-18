const basePath = "/v4beta"

/** @type {import('next').NextConfig} */

const nextConfig = {
  basePath,
  assetPrefix: '/v4beta',
  output: 'standalone',
  async redirects() {
    return [
      {
        source: "/",
        destination: basePath,
        basePath: false,
        permanent: true,
      },
    ]
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
};

export default nextConfig;