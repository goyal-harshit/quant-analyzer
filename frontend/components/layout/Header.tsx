'use client'

import { Search, Bell, User as UserIcon } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider'
import { usePathname } from 'next/navigation'

interface HeaderProps {
  onSearchClick: () => void
}

export default function Header({ onSearchClick }: HeaderProps) {
  const { user } = useAuth()
  const pathname = usePathname()

  const isAuthPage = pathname === '/login' || pathname === '/register'
  if (isAuthPage) return null

  return (
    <header className="fixed top-0 right-0 h-16 border-b border-border bg-card/50 backdrop-blur-md z-30 flex items-center justify-between px-6 transition-all duration-300 left-0 md:left-56 collapsed-sibling:left-16">
      {/* Search trigger */}
      <button 
        onClick={onSearchClick}
        className="flex items-center gap-3 px-4 py-2 bg-elevated/50 hover:bg-elevated border border-border hover:border-borderHi text-textMuted hover:text-textSub rounded-lg text-sm transition-all text-left w-64 max-w-full"
      >
        <Search className="w-4 h-4" />
        <span>Search stocks... (Ctrl+K)</span>
      </button>

      {/* Right side items */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="p-2 text-textSub hover:text-textPrimary hover:bg-elevated rounded-lg transition-colors border border-transparent hover:border-border relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-brand rounded-full"></span>
        </button>

        {/* User avatar/name */}
        <div className="flex items-center gap-3 border-l border-border pl-4">
          <div className="flex flex-col text-right hidden sm:flex">
            <span className="text-sm font-semibold text-textPrimary leading-none">{user?.email?.split('@')[0]}</span>
            <span className="text-xs text-textSub capitalize mt-1">{user?.plan} user</span>
          </div>
          <div className="w-9 h-9 rounded-full bg-brand/10 border border-brand/30 flex items-center justify-center text-brand">
            <UserIcon className="w-4 h-4" />
          </div>
        </div>
      </div>
    </header>
  )
}
