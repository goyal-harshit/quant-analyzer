// /frontend/components/layout/LayoutShell.tsx
'use client'

import { useState, useEffect } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import { usePathname } from 'next/navigation'
import CommandPalette from '../ui/CommandPalette'

interface LayoutShellProps {
  children: React.ReactNode
}

export default function LayoutShell({ children }: LayoutShellProps) {
  const [collapsed, setCollapsed] = useState(false)   // desktop rail collapse
  const [mobileOpen, setMobileOpen] = useState(false) // mobile off-canvas drawer
  const [isMobile, setIsMobile] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [isOffline, setIsOffline] = useState(false)
  const pathname = usePathname()
  const isStandalonePage = pathname === '/login' || pathname === '/register' || pathname === '/'

  // Track online status
  useEffect(() => {
    setIsOffline(!navigator.onLine)
    const onOnline = () => setIsOffline(false)
    const onOffline = () => setIsOffline(true)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  }, [])

  // Track viewport so the sidebar is a fixed rail on desktop but an off-canvas
  // drawer on mobile (where a 224px margin would crush the content).
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  // Close the mobile drawer whenever the route changes.
  useEffect(() => { setMobileOpen(false) }, [pathname])

  // Global Ctrl+K handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen(prev => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  if (isStandalonePage) {
    return <div className="min-h-screen bg-bg">{children}</div>
  }

  const sidebarWidth = collapsed ? 64 : 224
  const contentOffset = isMobile ? 0 : sidebarWidth

  return (
    <div className="min-h-screen bg-bg">
      {/* Sidebar — fixed rail (desktop) or off-canvas drawer (mobile) */}
      <Sidebar
        collapsed={!isMobile && collapsed}
        onToggle={() => setCollapsed(c => !c)}
        isMobile={isMobile}
        mobileOpen={mobileOpen}
      />

      {/* Mobile backdrop */}
      {isMobile && mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main column — offset by the rail on desktop, full-width on mobile */}
      <div
        className="flex flex-col min-h-screen transition-all duration-300"
        style={{ marginLeft: contentOffset }}
      >
        <Header
          onSearchClick={() => setSearchOpen(true)}
          contentOffset={contentOffset}
          isMobile={isMobile}
          onMenuClick={() => setMobileOpen(true)}
        />
        <main
          className="flex-1 overflow-auto"
          style={{ paddingTop: '64px' }} // header height
        >
          <div className="max-w-[1440px] mx-auto p-4 md:p-8 flex flex-col gap-6">
            {children}
          </div>
        </main>
      </div>

      {isOffline && (
        <div className="fixed bottom-4 right-4 bg-amber-500/10 border border-amber-500/30 text-amber-500 px-4 py-2.5 rounded-lg text-xs font-semibold shadow-lg backdrop-blur-md z-50 flex items-center gap-2 animate-bounce">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          <span>You are currently offline. Serving cached data.</span>
        </div>
      )}

      <CommandPalette isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  )
}
