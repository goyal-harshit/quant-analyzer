// /frontend/components/layout/LayoutShell.tsx
'use client'

import { useState } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import { usePathname } from 'next/navigation'
import CommandPalette from '../ui/CommandPalette'

interface LayoutShellProps {
  children: React.ReactNode
}

export default function LayoutShell({ children }: LayoutShellProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const pathname = usePathname()
  const isAuthPage = pathname === '/login' || pathname === '/register'

  if (isAuthPage) {
    return <div className="min-h-screen bg-bg">{children}</div>
  }

  const sidebarWidth = collapsed ? '64px' : '224px'

  return (
    <div className="min-h-screen bg-bg flex">
      {/* Sidebar */}
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} />

      {/* Main */}
      <div
        className="flex-1 flex flex-col min-h-screen transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <Header onSearchClick={() => setSearchOpen(true)} />
        <main
          className="flex-1 overflow-auto"
          style={{ paddingTop: '64px' }} // header height
        >
          <div className="max-w-[1440px] mx-auto p-4 md:p-8 flex flex-col gap-6">
            {children}
          </div>
        </main>
      </div>

      <CommandPalette isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  )
}
