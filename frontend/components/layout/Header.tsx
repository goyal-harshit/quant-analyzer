'use client'

import Link from 'next/link'
import { Search, Bell, User as UserIcon, Menu } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider'
import { usePathname } from 'next/navigation'

interface HeaderProps {
  onSearchClick: () => void
  contentOffset?: number
  isMobile?: boolean
  onMenuClick?: () => void
}

export default function Header({ onSearchClick, contentOffset = 224, isMobile = false, onMenuClick }: HeaderProps) {
  const { user } = useAuth()
  const pathname = usePathname()

  const isAuthPage = pathname === '/login' || pathname === '/register'
  if (isAuthPage) return null

  const active = (href: string) => pathname.startsWith(href)

  return (
    <header
      className="fixed top-0 right-0 h-16 border-b border-border bg-card/50 backdrop-blur-md z-30 flex items-center justify-between px-4 md:px-6 transition-all duration-300"
      style={{ left: contentOffset }}
    >
      {/* Left group: mobile menu + search */}
      <div className="flex items-center gap-2 min-w-0">
        {isMobile && (
          <button
            onClick={onMenuClick}
            aria-label="Open menu"
            className="p-2 rounded-lg text-textSub hover:text-textPrimary hover:bg-elevated transition-colors flex-shrink-0"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        {/* Search trigger */}
        <button
          onClick={onSearchClick}
          aria-label="Search stocks"
          className="flex items-center gap-3 px-3 md:px-4 py-2 bg-elevated/50 hover:bg-elevated border border-border hover:border-borderHi text-textMuted hover:text-textSub rounded-lg text-sm transition-all text-left w-40 sm:w-56 md:w-64"
        >
          <Search className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">Search<span className="hidden sm:inline"> stocks... (Ctrl+K)</span></span>
        </button>
      </div>

      {/* Right side items */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <Link
          href="/notifications"
          aria-label="Notifications"
          title="Notifications"
          className={`p-2 rounded-lg transition-colors border relative ${
            active('/notifications')
              ? 'text-brand bg-brand/10 border-brand/20'
              : 'text-textSub hover:text-textPrimary hover:bg-elevated border-transparent hover:border-border'
          }`}
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-brand rounded-full" aria-hidden="true">
            <span className="sr-only">You have new notifications</span>
          </span>
        </Link>

        {/* User avatar — links to profile */}
        <Link
          href="/profile"
          aria-label="Profile"
          title="Profile"
          className="flex items-center gap-3 border-l border-border pl-4 group"
        >
          <div className="flex-col text-right hidden sm:flex">
            <span className="text-sm font-semibold text-textPrimary leading-none">
              {user?.email?.split('@')[0] ?? 'Guest'}
            </span>
            <span className="text-xs text-textSub capitalize mt-1">{user?.plan ?? 'free'} user</span>
          </div>
          <div
            className={`w-9 h-9 rounded-full bg-brand/10 border flex items-center justify-center text-brand transition-colors ${
              active('/profile') ? 'border-brand' : 'border-brand/30 group-hover:border-brand/60'
            }`}
          >
            <UserIcon className="w-4 h-4" />
          </div>
        </Link>
      </div>
    </header>
  )
}
