import IndexDetailClient from './IndexDetailClient'
import { INDEX_LIST } from '@/lib/indices'

// Pre-render every index page for the static export (output: 'export').
export function generateStaticParams() {
  return INDEX_LIST.map((i) => ({ slug: i.slug }))
}

export default function IndexPage() {
  return <IndexDetailClient />
}
