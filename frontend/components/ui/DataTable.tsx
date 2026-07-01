'use client'

import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import { ArrowUp, ArrowDown, ChevronsUpDown } from 'lucide-react'

export interface ColumnDef<T> {
  header: string | React.ReactNode
  accessorKey?: string
  cell?: (row: T) => React.ReactNode
  sortable?: boolean
  align?: 'left' | 'right' | 'center'
}

interface DataTableProps<T> {
  columns: ColumnDef<T>[]
  data: T[]
  onRowClick?: (row: T) => void
  isLoading?: boolean
  loadingMessage?: string
  emptyMessage?: string
  className?: string
}

export default function DataTable<T>({
  columns,
  data,
  onRowClick,
  isLoading = false,
  loadingMessage = 'Loading data...',
  emptyMessage = 'No results found.',
  className,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(p => (p === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sortedData = React.useMemo(() => {
    if (!sortKey) return data

    return [...data].sort((a: any, b: any) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]

      if (aVal === bVal) return 0
      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1

      const modifier = sortDir === 'asc' ? 1 : -1

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return (aVal - bVal) * modifier
      }

      return String(aVal).localeCompare(String(bVal)) * modifier
    })
  }, [data, sortKey, sortDir])

  return (
    <div className={cn('overflow-x-auto w-full border border-border rounded-xl bg-card', className)}>
      <table className="w-full text-left border-collapse text-sm">
        <thead>
          <tr className="border-b border-border bg-elevated/40 text-textMuted text-xs font-semibold uppercase">
            {columns.map((col, idx) => {
              const alignClass = 
                col.align === 'right' ? 'text-right' : 
                col.align === 'center' ? 'text-center' : 
                'text-left'

              const isSortable = col.sortable && col.accessorKey

              return (
                <th
                  key={idx}
                  className={cn(
                    'py-3.5 px-4 font-semibold select-none', 
                    alignClass,
                    isSortable && 'cursor-pointer hover:text-textPrimary transition-colors'
                  )}
                  onClick={() => isSortable && handleSort(col.accessorKey!)}
                >
                  <div className={cn('flex items-center gap-1.5', col.align === 'right' && 'justify-end', col.align === 'center' && 'justify-center')}>
                    <span>{col.header}</span>
                    {isSortable && (
                      <span className="text-textMuted">
                        {sortKey === col.accessorKey ? (
                          sortDir === 'asc' ? (
                            <ArrowUp className="w-3 h-3 text-brand" />
                          ) : (
                            <ArrowDown className="w-3 h-3 text-brand" />
                          )
                        ) : (
                          <ChevronsUpDown className="w-3 h-3 opacity-40 hover:opacity-100" />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/30 text-textPrimary">
          {isLoading ? (
            <tr>
              <td colSpan={columns.length} className="py-8 text-center text-textMuted text-xs">
                <span className="inline-block animate-spin mr-2">⏳</span>
                {loadingMessage}
              </td>
            </tr>
          ) : sortedData.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="py-8 text-center text-textMuted text-xs">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedData.map((row, rIdx) => (
              <tr
                key={rIdx}
                className={cn(
                  'hover:bg-elevated/20 transition-colors',
                  onRowClick && 'cursor-pointer'
                )}
                onClick={() => onRowClick && onRowClick(row)}
              >
                {columns.map((col, cIdx) => {
                  const alignClass = 
                    col.align === 'right' ? 'text-right' : 
                    col.align === 'center' ? 'text-center' : 
                    'text-left'

                  const cellVal = col.cell 
                    ? col.cell(row) 
                    : col.accessorKey 
                      ? (row as any)[col.accessorKey] 
                      : ''

                  return (
                    <td
                      key={cIdx}
                      className={cn('py-3 px-4', alignClass)}
                    >
                      {cellVal}
                    </td>
                  )
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
