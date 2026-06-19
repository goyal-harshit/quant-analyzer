import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  stocksApi, 
  screenerApi, 
  portfolioApi, 
  watchlistsApi, 
  alertsApi,
  backtestApi,
  dashboardApi,
  macroApi
} from './api'

// ── STOCKS HOOKS ───────────────────────────────────────────────────
export function useStockSearch(query: string) {
  return useQuery({
    queryKey: ['stocks', 'search', query],
    queryFn: () => stocksApi.search(query),
    enabled: query.length > 1,
  })
}

export function useStockQuote(ticker: string, refreshSeed = 0) {
  return useQuery({
    queryKey: ['stocks', 'quote', ticker, refreshSeed],
    queryFn: () => stocksApi.getQuote(ticker, refreshSeed > 0),
    enabled: !!ticker,
    refetchInterval: 15000, // Refresh quotes every 15s
  })
}

export function useStockFundamentals(ticker: string, refreshSeed = 0) {
  return useQuery({
    queryKey: ['stocks', 'fundamentals', ticker, refreshSeed],
    queryFn: () => stocksApi.getFundamentals(ticker, refreshSeed > 0),
    enabled: !!ticker,
  })
}

export function useStockHistory(ticker: string, period = '1y', refreshSeed = 0) {
  return useQuery({
    queryKey: ['stocks', 'history', ticker, period, refreshSeed],
    queryFn: () => stocksApi.getHistory(ticker, period, refreshSeed > 0),
    enabled: !!ticker,
  })
}

export function useStockTechnicals(ticker: string) {
  return useQuery({
    queryKey: ['stocks', 'technicals', ticker],
    queryFn: () => stocksApi.getTechnicals(ticker),
    enabled: !!ticker,
  })
}

// ── SCREENER HOOKS ─────────────────────────────────────────────────
export function useScreener(filters: any, refreshSeed = 0) {
  return useQuery({
    queryKey: ['screener', filters, refreshSeed],
    queryFn: () => screenerApi.screen({ ...filters, refresh: refreshSeed > 0 }),
  })
}

export function useSectors() {
  return useQuery({
    queryKey: ['sectors'],
    queryFn: () => screenerApi.getSectors(),
  })
}

// ── PORTFOLIO HOOKS ────────────────────────────────────────────────
export function usePortfolios() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => portfolioApi.list(),
  })
}

export function usePortfolio(id: number, refreshSeed = 0) {
  return useQuery({
    queryKey: ['portfolio', id, refreshSeed],
    queryFn: () => portfolioApi.get(id, refreshSeed > 0),
    enabled: !!id,
  })
}

export function usePortfolioSectorAllocation(id: number) {
  return useQuery({
    queryKey: ['portfolio', id, 'sectors'],
    queryFn: () => portfolioApi.getSectorAllocation(id),
    enabled: !!id,
  })
}

export function usePortfolioPerformance(id: number, benchmark = 'NIFTY50', period = '1y', refreshSeed = 0) {
  return useQuery({
    queryKey: ['portfolio', id, 'performance', benchmark, period, refreshSeed],
    queryFn: () => portfolioApi.getPerformance(id, benchmark, period, refreshSeed > 0),
    enabled: !!id,
  })
}


export function useCreatePortfolio() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; description?: string; benchmark?: string }) => portfolioApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}

export function useAddPosition() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, position }: { id: number; position: any }) => portfolioApi.addPosition(id, position),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['portfolio', variables.id] })
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}

export function useRemovePosition() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, positionId }: { portfolioId: number; positionId: number }) =>
      portfolioApi.removePosition(portfolioId, positionId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['portfolio', variables.portfolioId] })
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}

export function useDeletePortfolio() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => portfolioApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}

// ── WATCHLISTS HOOKS ──────────────────────────────────────────────
export function useWatchlists() {
  return useQuery({
    queryKey: ['watchlists'],
    queryFn: () => watchlistsApi.list(),
  })
}

export function useWatchlist(id: number, refreshSeed = 0) {
  return useQuery({
    queryKey: ['watchlist', id, refreshSeed],
    queryFn: () => watchlistsApi.get(id, refreshSeed > 0),
    enabled: !!id,
    refetchInterval: 15000,
  })
}

export function useCreateWatchlist() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; tickers?: string[] }) => watchlistsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] })
    },
  })
}

export function useUpdateWatchlistTickers() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, tickers }: { id: number; tickers: string[] }) => watchlistsApi.updateTickers(id, tickers),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['watchlist', variables.id] })
      queryClient.invalidateQueries({ queryKey: ['watchlists'] })
    },
  })
}

export function useDeleteWatchlist() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => watchlistsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] })
    },
  })
}

// ── ALERTS HOOKS ───────────────────────────────────────────────────
export function useAlerts() {
  return useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertsApi.list(),
  })
}

export function useCreateAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { ticker: string; condition_type: string; threshold: number }) => alertsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useDeleteAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => alertsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

// ── DASHBOARD HOOKS ────────────────────────────────────────────────
export function useMarketSummary(refreshSeed = 0) {
  return useQuery({
    queryKey: ['dashboard', 'market-summary', refreshSeed],
    queryFn: () => dashboardApi.getMarketSummary(refreshSeed > 0),
    refetchInterval: 30000,
  })
}

export function useTopGainersLosers(refreshSeed = 0) {
  return useQuery({
    queryKey: ['dashboard', 'top-gainers-losers', refreshSeed],
    queryFn: () => dashboardApi.getTopGainersLosers(refreshSeed > 0),
    refetchInterval: 30000,
  })
}

export function useSectorPerformance(refreshSeed = 0) {
  return useQuery({
    queryKey: ['dashboard', 'sector-performance', refreshSeed],
    queryFn: () => dashboardApi.getSectorPerformance(refreshSeed > 0),
    refetchInterval: 60000,
  })
}

export function useFactorSignals(refreshSeed = 0) {
  return useQuery({
    queryKey: ['dashboard', 'factor-signals', refreshSeed],
    queryFn: () => dashboardApi.getFactorSignals(refreshSeed > 0),
    refetchInterval: 60000,
  })
}

// ── STOCK INSIGHT (consolidated — single call replaces 4+ sequential) ──
export function useStockInsight(ticker: string, includeAi = false, refreshSeed = 0) {
  return useQuery({
    queryKey: ['stocks', 'insight', ticker, includeAi, refreshSeed],
    queryFn: () => import('./api').then(m => m.insightApi.getStockInsight(ticker, includeAi, refreshSeed > 0)),
    enabled: !!ticker,
    staleTime: 15000,
    refetchInterval: 30000,
  })
}

// ── MACRO HOOKS ───────────────────────────────────────────────────
export function useMacroIndicators() {
  return useQuery({
    queryKey: ['macro', 'indicators'],
    queryFn: () => macroApi.getIndicators(),
  })
}
