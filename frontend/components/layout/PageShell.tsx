'use client'

import React from 'react'

interface PageShellProps {
  title: string
  subtitle?: string
  children: React.ReactNode
  actions?: React.ReactNode
}

export default function PageShell({ title, subtitle, children, actions }: PageShellProps) {
  return (
    <div className="p-6 md:p-8 pt-24 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-textPrimary">{title}</h1>
          {subtitle && <p className="text-sm text-textSub mt-1">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
      <div className="w-full">
        {children}
      </div>
    </div>
  )
}
