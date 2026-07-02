import StockDetailClient from './StockDetailClient'
import { NIFTY_500_TICKERS } from '@/lib/tickers'

// Pre-render every stock in the universe for the static export (output:
// 'export') — any ticker missing here 500s when opened from the dashboard,
// search, or screener, since there's no server to generate it on demand.
export function generateStaticParams() {
  return NIFTY_500_TICKERS.map((ticker) => ({ ticker }))
}

export default function StockPage() {
  return <StockDetailClient />
}
