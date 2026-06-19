import type { Metadata } from 'next'
import './globals.css'
import QueryProvider from '@/components/providers/QueryProvider'
import { AuthProvider } from '@/components/auth/AuthProvider'
import LayoutShell from '@/components/layout/LayoutShell'

export const metadata: Metadata = {
  title: 'QuantAI - India-First Quantitative Investment Analyzer',
  description: 'AI-powered quantitative investment analytics platform for Indian equities',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-bg text-textPrimary">
        <QueryProvider>
          <AuthProvider>
            <LayoutShell>
              {children}
            </LayoutShell>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
