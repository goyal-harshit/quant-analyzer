/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  basePath: '/quant-analyzer',
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
