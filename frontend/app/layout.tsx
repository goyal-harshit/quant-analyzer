import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import QueryProvider from '@/components/providers/QueryProvider'
import { AuthProvider } from '@/components/auth/AuthProvider'
import { ThemeProvider, themeNoFlashScript } from '@/components/providers/ThemeProvider'
import LayoutShell from '@/components/layout/LayoutShell'
import PwaRegister from '@/components/providers/PwaRegister'

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''

export const metadata: Metadata = {
  title: 'QuantAI - India-First Quantitative Investment Analyzer',
  description: 'AI-powered quantitative investment analytics platform for Indian equities',
  applicationName: 'QuantAI',
  manifest: `${basePath}/manifest.webmanifest`,
  appleWebApp: {
    capable: true,
    title: 'QuantAI',
    statusBarStyle: 'black-translucent',
  },
  icons: {
    icon: `${basePath}/icon.svg`,
    apple: `${basePath}/icon.svg`,
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#0a1020',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* No-flash theme: set the html class from localStorage before paint. */}
        <script dangerouslySetInnerHTML={{ __html: themeNoFlashScript }} />
      </head>
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
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              <PwaRegister />
              <LayoutShell>
                {children}
              </LayoutShell>
              <Toaster
                position="top-right"
                toastOptions={{
                  style: {
                    background: 'var(--elevated)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border)',
                    fontSize: '13px',
                  },
                }}
              />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
