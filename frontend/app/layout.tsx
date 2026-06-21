import type { Metadata } from 'next'
import './globals.css'
import { Toaster } from 'react-hot-toast'
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
        {/* Font links — Next.js App Router hoists <link> tags into <head>.
            Avoids a render-blocking CSS @import while staying hydration-safe
            (no manual <head> element, which App Router manages itself). */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
        />
        <QueryProvider>
          <AuthProvider>
            <LayoutShell>
              {children}
            </LayoutShell>
            <Toaster
              position="top-right"
              toastOptions={{
                style: { background: '#0f182e', color: '#e2e8f0', border: '1px solid #1e2d4a', fontSize: '13px' },
              }}
            />
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
