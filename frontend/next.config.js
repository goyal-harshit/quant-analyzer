/** @type {import('next').NextConfig} */
// basePath is ONLY for GitHub Pages, which serves the app under /quant-analyzer.
// It must be empty everywhere else (local dev, Docker/nginx served at root),
// otherwise every asset is requested under /quant-analyzer/_next/... which 404s,
// the JS never loads, React never hydrates, and the whole page is dead.
//
// Driven by an explicit env var (NOT NODE_ENV) so the Docker production build can
// stay NODE_ENV=production for optimization while still serving at root. The
// GitHub Pages workflow sets NEXT_PUBLIC_BASE_PATH=/quant-analyzer.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''

const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  basePath,
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
