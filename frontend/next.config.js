/** @type {import('next').NextConfig} */
// basePath is only needed for the production static export (GitHub Pages serves
// the app under /quant-analyzer). In local dev that prefix makes every route
// 404 at localhost:3000/, so apply it for production builds only.
const isProd = process.env.NODE_ENV === 'production'

const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  basePath: isProd ? '/quant-analyzer' : '',
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
