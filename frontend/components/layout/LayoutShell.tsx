'use client'

import { usePathname } from 'next/navigation'
import Sidebar from './Sidebar'
import { T } from '@/lib/stockData'

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isAuthPage = pathname === '/login' || pathname === '/register'

  if (isAuthPage) {
    return (
      <div style={{
        minHeight: '100vh', background: T.bg, color: T.text,
        fontFamily: T.sans, display: 'flex', flexDirection: 'column',
        justifyContent: 'center',
      }}>
        {children}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', background: T.bg, minHeight: '100vh', color: T.text, fontFamily: T.sans }}>
      <style>{`
        *{box-sizing:border-box;margin:0;padding:0;}
        ::-webkit-scrollbar{width:5px;height:5px;}
        ::-webkit-scrollbar-track{background:${T.bg};}
        ::-webkit-scrollbar-thumb{background:${T.b};border-radius:3px;}
        select option{background:${T.el};}
        @keyframes spin{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}
      `}</style>
      <Sidebar />
      <main style={{ marginLeft: 215, flex: 1, overflowY: 'auto', minHeight: '100vh' }}>
        {children}
      </main>
    </div>
  )
}
