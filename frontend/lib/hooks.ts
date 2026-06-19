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

export function useStockQuote(ticker: string) {
  return useQuery({
    queryKey: ['stocks', 'quote', ticker],
    queryFn: () => stocksApi.getQuote(ticker),
    enabled: !!ticker,
    refetchInterval: 15000, // Refresh quotes every 15s
  })
}

export function useStockFundamentals(ticker: string) {
  return useQuery({
    queryKey: ['stocks', 'fundamentals', ticker],
    queryFn: () => stocksApi.getFundamentals(ticker),
    enabled: !!ticker,
  })
}

export function useStockHistory(ticker: string, period = '1y') {
  return useQuery({
    queryKey: ['stocks', 'history', ticker, period],
    queryFn: () => stocksApi.getHistory(ticker, period),
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
export function useScreener(filters: any) {
  return useQuery({
    queryKey: ['screener', filters],
    queryFn: () => screenerApi.screen(filters),
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

export function usePortfolio(id: number) {
  return useQuery({
    queryKey: ['portfolio', id],
    queryFn: () => portfolioApi.get(id),
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

export function useWatchlist(id: number) {
  return useQuery({
    queryKey: ['watchlist', id],
    queryFn: () => watchlistsApi.get(id),
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
export function useMarketSummary() {
  return useQuery({
    queryKey: ['dashboard', 'market-summary'],
    queryFn: () => dashboardApi.getMarketSummary(),
    refetchInterval: 30000,
  })
}

export function useTopGainersLosers() {
  return useQuery({
    queryKey: ['dashboard', 'top-gainers-losers'],
    queryFn: () => dashboardApi.getTopGainersLosers(),
    refetchInterval: 30000,
  })
}

export function useSectorPerformance() {
  return useQuery({
    queryKey: ['dashboard', 'sector-performance'],
    queryFn: () => dashboardApi.getSectorPerformance(),
    refetchInterval: 60000,
  })
}

export function useFactorSignals() {
  return useQuery({
    queryKey: ['dashboard', 'factor-signals'],
    queryFn: () => dashboardApi.getFactorSignals(),
    refetchInterval: 60000,
  })
}

// ── STOCK INSIGHT (consolidated — single call replaces 4+ sequential) ──
export function useStockInsight(ticker: string, includeAi = false) {
  return useQuery({
    queryKey: ['stocks', 'insight', ticker, includeAi],
    queryFn: () => import('./api').then(m => m.insightApi.getStockInsight(ticker, includeAi)),
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
