'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Star, Trash2, Plus, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'
import { T, pct, scoreColor } from '@/lib/stockData'
import {
  useWatchlists,
  useWatchlist,
  useCreateWatchlist,
  useUpdateWatchlistTickers,
  useDeleteWatchlist
} from '@/lib/hooks'
import { stocksApi } from '@/lib/api'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

export default function WatchlistsPage() {
  const router = useRouter()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [newWatchlistName, setNewWatchlistName] = useState('')
  const [tickerToAdd, setTickerToAdd] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [refreshSeed, setRefreshSeed] = useState(0)

  // Watchlists hooks
  const { data: watchlists = [], isLoading: listsLoading } = useWatchlists()
  const createMutation = useCreateWatchlist()
  const deleteMutation = useDeleteWatchlist()
  const updateTickersMutation = useUpdateWatchlistTickers()

  // Automatically select the first watchlist if none selected.
  // Must run in an effect — calling setState during render triggers
  // "Cannot update a component while rendering" and risks re-render loops.
  useEffect(() => {
    if (watchlists.length > 0 && selectedId === null) {
      setSelectedId(watchlists[0].id)
    }
  }, [watchlists, selectedId])

  // Fetch selected watchlist details (which includes live quotes)
  const { data: activeList, isLoading: listLoading } = useWatchlist(selectedId || 0, refreshSeed)

  const handleCreateWatchlist = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newWatchlistName.trim()) return
    createMutation.mutate({ name: newWatchlistName.trim(), tickers: [] }, {
      onSuccess: (data) => {
        setNewWatchlistName('')
        if (data && data.id) {
          setSelectedId(data.id)
        }
      }
    })
  }

  const handleDeleteWatchlist = () => {
    if (!selectedId) return
    if (confirm('Are you sure you want to delete this watchlist?')) {
      deleteMutation.mutate(selectedId, {
        onSuccess: () => {
          setSelectedId(watchlists.find((w: any) => w.id !== selectedId)?.id || null)
        }
      })
    }
  }

  const handleAddTicker = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedId || !activeList || !tickerToAdd.trim()) return
    const symbol = tickerToAdd.trim().toUpperCase()

    // Add ticker and update
    const currentTickers = activeList.tickers || []
    if (currentTickers.includes(symbol)) {
      alert('Ticker is already in this watchlist')
      return
    }

    updateTickersMutation.mutate({
      id: selectedId,
      tickers: [...currentTickers, symbol]
    }, {
      onSuccess: () => {
        setTickerToAdd('')
      }
    })
  }

  const handleRemoveTicker = (symbol: string) => {
    if (!selectedId || !activeList) return
    const currentTickers = activeList.tickers || []
    updateTickersMutation.mutate({
      id: selectedId,
      tickers: currentTickers.filter((t: string) => t !== symbol)
    })
  }

  const tickersList = activeList?.tickers || []
  const quotesMap = activeList?.quotes || {}

  const filteredTickers = tickersList.filter((t: string) => {
    const quote = quotesMap[t]
    const name = quote?.name || ''
    return t.includes(searchQuery.toUpperCase()) || name.toLowerCase().includes(searchQuery.toLowerCase())
  })

  const isLoading = listsLoading || listLoading

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1400, fontFamily: T.sans }}>
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Personal Watchlists</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
            Monitor and track your favorite quantitative constituents in real-time
          </div>
        </div>
        {selectedId && (
          <button 
            onClick={() => setRefreshSeed(prev => prev + 1)} 
            style={{
              marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', background: T.el, border: `1px solid ${T.b}`,
              borderRadius: 6, fontSize: 12, color: T.sub, cursor: 'pointer'
            }}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh Quotes
          </button>
        )}
      </div>

      {/* Control panel: Select and Create */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16, marginBottom: 18 }}>
        <div style={card({ padding: '14px 18px', display: 'flex', gap: 12, alignItems: 'center' })}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>SELECT WATCHLIST</div>
            {watchlists.length === 0 ? (
              <div style={{ fontSize: 12, color: T.sub }}>No watchlists found. Create one.</div>
            ) : (
              <select
                value={selectedId || ''}
                onChange={e => setSelectedId(Number(e.target.value))}
                style={{
                  width: '100%', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                  padding: '8px 10px', fontSize: 12, color: T.text, cursor: 'pointer',
                }}
              >
                {watchlists.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            )}
          </div>
          {selectedId && (
            <button
              onClick={handleDeleteWatchlist}
              style={{
                background: 'transparent', border: 'none', color: T.red, cursor: 'pointer',
                padding: '8px', marginTop: 14, display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}
              title="Delete Watchlist"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          )}
        </div>

        <div style={card({ padding: '14px 18px' })}>
          <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>CREATE NEW WATCHLIST</div>
          <form onSubmit={handleCreateWatchlist} style={{ display: 'flex', gap: 8 }}>
            <input
              value={newWatchlistName}
              onChange={e => setNewWatchlistName(e.target.value)}
              placeholder="e.g. My Bluechips"
              style={{
                flex: 1, background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                padding: '8px 12px', fontSize: 12, color: T.text, outline: 'none',
              }}
            />
            <button
              type="submit"
              style={{
                background: T.blue, border: 'none', borderRadius: 6, padding: '8px 16px',
                color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4
              }}
            >
              <Plus className="w-4 h-4" /> Create
            </button>
          </form>
        </div>
      </div>

      {selectedId && activeList && (
        <>
          {/* Watchlist tools: Add stock and search */}
          <div style={card({ padding: '14px 18px', marginBottom: 18, display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' })}>
            <form onSubmit={handleAddTicker} style={{ display: 'flex', gap: 8, flex: 1, maxWidth: 350 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>ADD STOCK TO WATCHLIST</div>
                <input
                  value={tickerToAdd}
                  onChange={e => setTickerToAdd(e.target.value)}
                  placeholder="e.g. RELIANCE"
                  style={{
                    width: '100%', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                    padding: '8px 12px', fontSize: 12, color: T.text, outline: 'none',
                  }}
                />
              </div>
              <button
                type="submit"
                style={{
                  background: T.blue, border: 'none', borderRadius: 6, padding: '8px 16px',
                  color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer', height: 35, marginTop: 14
                }}
              >
                Add
              </button>
            </form>

            <div style={{ marginLeft: 'auto', width: 220 }}>
              <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>SEARCH IN LIST</div>
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search symbol..."
                style={{
                  width: '100%', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                  padding: '8px 12px', fontSize: 12, color: T.text, outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Watchlist table */}
          <div style={card({ overflow: 'auto' })}>
            {isLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0', gap: 10 }}>
                <RefreshCw className="w-6 h-6 text-brand animate-spin" />
                <span style={{ fontSize: 12, color: T.sub }}>Syncing watchlist details...</span>
              </div>
            ) : filteredTickers.length === 0 ? (
              <div style={{ padding: 40, textAlign: 'center', color: T.muted, fontSize: 13 }}>
                No constituents found in this watchlist. Add some above.
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${T.b}` }}>
                    {['Ticker', 'Name', 'Sector', 'Price', 'Chg%', 'Score', 'Actions'].map(h => (
                      <th key={h} style={{
                        padding: '10px 13px', fontSize: 10, textTransform: 'uppercase',
                        letterSpacing: '0.06em', color: T.muted, fontWeight: 600,
                        textAlign: h === 'Ticker' || h === 'Name' || h === 'Sector' ? 'left' : h === 'Actions' ? 'center' : 'right',
                        whiteSpace: 'nowrap',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredTickers.map((ticker: string, i: number) => {
                    const stk = quotesMap[ticker] || { ticker, name: ticker, sector: 'Unknown', price: 0, change_pct: 0 }
                    const isPos = (stk.change_pct ?? 0) >= 0
                    // Seed data or cached fallback composite score
                    const composite = (stk as any).composite_score ?? 60

                    return (
                      <tr
                        key={ticker}
                        style={{
                          borderBottom: `1px solid ${T.b}`,
                          background: i % 2 === 0 ? 'transparent' : `${T.el}66`,
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = T.el }}
                        onMouseLeave={e => { e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : `${T.el}66` }}
                      >
                        <td style={{ padding: '9px 13px' }}>
                          <Link href={`/stocks/${ticker}`} style={{
                            fontFamily: T.mono, fontWeight: 700, fontSize: 12,
                            color: T.blue, textDecoration: 'none',
                          }}>
                            {ticker}
                          </Link>
                        </td>
                        <td style={{ padding: '9px 13px', fontSize: 12, color: T.text }}>{stk.name || ticker}</td>
                        <td style={{ padding: '9px 13px' }}>
                          <span style={{
                            background: `${T.purple}22`, color: T.purple,
                            border: `1px solid ${T.purple}44`, borderRadius: 4,
                            padding: '2px 7px', fontSize: 10, fontWeight: 700,
                          }}>{stk.sector || 'Unknown'}</span>
                        </td>
                        <td style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>
                          ₹{stk.price ? stk.price.toLocaleString('en-IN') : 'N/A'}
                        </td>
                        <td style={{
                          padding: '9px 13px', textAlign: 'right', fontFamily: T.mono,
                          fontSize: 12, color: isPos ? T.green : T.red,
                        }}>
                          {pct(stk.change_pct ?? 0)}
                        </td>
                        <td style={{ padding: '9px 13px', textAlign: 'right' }}>
                          <span style={{
                            background: `${scoreColor(composite)}22`,
                            color: scoreColor(composite),
                            border: `1px solid ${scoreColor(composite)}44`,
                            borderRadius: 4, padding: '2px 9px', fontSize: 12,
                            fontFamily: T.mono, fontWeight: 700,
                          }}>{composite}</span>
                        </td>
                        <td style={{ padding: '9px 13px', textAlign: 'center' }}>
                          <button
                            onClick={() => handleRemoveTicker(ticker)}
                            style={{
                              background: 'transparent', border: 'none', color: T.red, cursor: 'pointer',
                              padding: 4
                            }}
                            title="Remove Stock"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  )
}
