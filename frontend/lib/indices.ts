// Shared index registry for slug-based routing (static-export friendly — avoids
// the '^' in Yahoo symbols appearing in URL/file paths).

export interface IndexRef {
  slug: string
  symbol: string
  name: string
}

export const INDEX_LIST: IndexRef[] = [
  { slug: 'nifty-50', symbol: '^NSEI', name: 'NIFTY 50' },
  { slug: 'sensex', symbol: '^BSESN', name: 'SENSEX' },
  { slug: 'nifty-next-50', symbol: '^NSMIDCP', name: 'NIFTY NEXT 50' },
  { slug: 'nifty-500', symbol: '^CRSLDX', name: 'NIFTY 500' },
  { slug: 'nifty-midcap-50', symbol: '^NSEMDCP50', name: 'NIFTY MIDCAP 50' },
  { slug: 'bank-nifty', symbol: '^NSEBANK', name: 'BANK NIFTY' },
  { slug: 'nifty-fin-service', symbol: 'NIFTY_FIN_SERVICE.NS', name: 'NIFTY FIN SERVICE' },
  { slug: 'nifty-it', symbol: '^CNXIT', name: 'NIFTY IT' },
  { slug: 'nifty-auto', symbol: '^CNXAUTO', name: 'NIFTY AUTO' },
  { slug: 'nifty-pharma', symbol: '^CNXPHARMA', name: 'NIFTY PHARMA' },
  { slug: 'nifty-fmcg', symbol: '^CNXFMCG', name: 'NIFTY FMCG' },
  { slug: 'nifty-metal', symbol: '^CNXMETAL', name: 'NIFTY METAL' },
  { slug: 'nifty-realty', symbol: '^CNXREALTY', name: 'NIFTY REALTY' },
  { slug: 'nifty-energy', symbol: '^CNXENERGY', name: 'NIFTY ENERGY' },
  { slug: 'nifty-infra', symbol: '^CNXINFRA', name: 'NIFTY INFRA' },
  { slug: 'nifty-media', symbol: '^CNXMEDIA', name: 'NIFTY MEDIA' },
  { slug: 'nifty-psu-bank', symbol: '^CNXPSUBANK', name: 'NIFTY PSU BANK' },
  { slug: 'nifty-pse', symbol: '^CNXPSE', name: 'NIFTY PSE' },
  { slug: 'india-vix', symbol: '^INDIAVIX', name: 'INDIA VIX' },
]

const _bySlug = Object.fromEntries(INDEX_LIST.map((i) => [i.slug, i]))
const _bySymbol = Object.fromEntries(INDEX_LIST.map((i) => [i.symbol, i]))
const _byName = Object.fromEntries(INDEX_LIST.map((i) => [i.name, i]))

export const slugToSymbol = (slug: string): string | undefined => _bySlug[slug]?.symbol
export const symbolToSlug = (symbol: string): string | undefined => _bySymbol[symbol]?.slug
export const nameToSlug = (name: string): string | undefined => _byName[name]?.slug
