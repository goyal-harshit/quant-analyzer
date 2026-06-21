import StockDetailClient from './StockDetailClient'

export function generateStaticParams() {
  const tickers = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
    'HINDUNILVR', 'SBIN', 'BHARTIARTL', 'ITC', 'KOTAKBANK',
    'LT', 'AXISBANK', 'WIPRO', 'HCLTECH', 'ASIANPAINT',
    'MARUTI', 'SUNPHARMA', 'TITAN', 'BAJFINANCE', 'NESTLEIND',
    'ULTRACEMCO', 'POWERGRID', 'NTPC', 'ONGC', 'JSWSTEEL',
  ]
  return tickers.map((ticker) => ({ ticker }))
}

export default function StockPage() {
  return <StockDetailClient />
}
