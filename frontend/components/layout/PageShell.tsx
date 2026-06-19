// /frontend/components/layout/PageShell.tsx
import React from 'react'

interface PageShellProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode     // right-side action buttons
  children: React.ReactNode
}

export default function PageShell({ title, subtitle, actions, children }: PageShellProps) {
  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{title}</h1>
          {subtitle && (
            <p className="text-sm text-textSub mt-1">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="flex items-center gap-2 flex-shrink-0 pt-1">
            {actions}
          </div>
        )}
      </div>

      {/* Page Content */}
      {children}
    </div>
  )
}
