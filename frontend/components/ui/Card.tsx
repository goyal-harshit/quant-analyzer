// /frontend/components/ui/Card.tsx
import React from 'react'
import { cn } from '@/lib/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'sm' | 'md' | 'lg' | 'none'
  variant?: 'default' | 'elevated' | 'bordered'
}

const paddingMap = {
  none: '',
  sm: 'p-3',
  md: 'p-5',     // standard — 20px
  lg: 'p-6',     // large — 24px
}

export default function Card({
  children, className, padding = 'md', variant = 'default'
}: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border shadow-card',
        variant === 'default'  && 'bg-card border-border',
        variant === 'elevated' && 'bg-elevated border-borderHi',
        variant === 'bordered' && 'bg-transparent border-borderHi',
        paddingMap[padding],
        className
      )}
    >
      {children}
    </div>
  )
}

// Card.Header — standard inner header with title + optional right slot
Card.Header = function CardHeader({
  title, subtitle, right, icon: Icon
}: {
  title: string
  subtitle?: string
  right?: React.ReactNode
  icon?: React.ElementType
}) {
  return (
    <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 text-brand" />}
        <div>
          <div className="card-title">{title}</div>
          {subtitle && <div className="text-xs text-textMuted mt-0.5">{subtitle}</div>}
        </div>
      </div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </div>
  )
}
