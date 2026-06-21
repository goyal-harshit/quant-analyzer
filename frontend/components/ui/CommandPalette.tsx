'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Sparkles } from 'lucide-react'
import { stocksApi } from '@/lib/api'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

interface StockSearchResult {
  ticker: string
  name: string
  sector: string
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockSearchResult[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [searching, setSearching] = useState(false)
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)

  // Keep keyboard focus inside the dialog while it's open (focus trap).
  const handleTrapKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== 'Tab') return
    const focusables = dialogRef.current?.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    if (!focusables || focusables.length === 0) return
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    const active = document.activeElement
    if (e.shiftKey && active === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && active === last) {
      e.preventDefault()
      first.focus()
    }
  }

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
      setQuery('')
      setResults([])
      setSelectedIndex(0)
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  // Handle click outside / close hotkey
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Search effect
  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }

    const delayDebounce = setTimeout(async () => {
      setSearching(true)
      try {
        const res = await stocksApi.search(query)
        setResults(res.results || [])
      } catch (err) {
        console.error(err)
      } finally {
        setSearching(false)
      }
    }, 200)

    return () => clearTimeout(delayDebounce)
  }, [query])

  // Handle arrows and Enter
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, results.length))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev - 1 + results.length) % Math.max(1, results.length))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (results[selectedIndex]) {
        handleSelect(results[selectedIndex].ticker)
      }
    }
  }

  const handleSelect = (ticker: string) => {
    router.push(`/stocks/${ticker.toUpperCase()}`)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4 bg-bg/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Stock search"
        className="w-full max-w-lg glass-elevated rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleTrapKeyDown}
      >
        {/* Search header */}
        <div className="flex items-center px-4 border-b border-border">
          <Search className="w-5 h-5 text-textSub mr-3" />
          <input
            ref={inputRef}
            type="text"
            className="w-full py-4 bg-transparent text-textPrimary placeholder-textMuted text-sm outline-none border-none"
            placeholder="Type a ticker or company name (e.g. RELIANCE)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

        {/* Results body */}
        <div className="max-h-72 overflow-y-auto p-2">
          {searching && (
            <div className="text-center py-6 text-sm text-textSub">Searching...</div>
          )}

          {!searching && results.length === 0 && query.trim() && (
            <div className="text-center py-6 text-sm text-textSub">No stocks found matching "{query}"</div>
          )}

          {!searching && results.length === 0 && !query.trim() && (
            <div className="text-center py-8 text-xs text-textMuted flex flex-col items-center gap-2">
              <Sparkles className="w-5 h-5 text-brand/50" />
              <span>Search across 500+ Indian stocks, sectors or indexes</span>
            </div>
          )}

          {!searching && results.length > 0 && (
            <div className="space-y-0.5">
              {results.map((item, idx) => (
                <button
                  key={item.ticker}
                  onClick={() => handleSelect(item.ticker)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-all ${
                    idx === selectedIndex 
                      ? 'bg-brand/10 border border-brand/20 text-textPrimary' 
                      : 'text-textSub hover:text-textPrimary hover:bg-elevated/30 border border-transparent'
                  }`}
                >
                  <div>
                    <div className="font-mono text-sm font-semibold">{item.ticker}</div>
                    <div className="text-xs text-textSub mt-0.5">{item.name}</div>
                  </div>
                  <div className="text-xs px-2 py-1 rounded bg-elevated/80 border border-border font-medium text-textSub">
                    {item.sector}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
