/**
 * QuantAI API Client
 * Typed wrapper around the FastAPI backend.
 */

import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const client = axios.create({
  baseURL: API_BASE,
  // 45s is plenty for data/quote calls. Long-running LLM calls pass a per-request
  // override where needed rather than making every request wait up to 2 minutes.
  timeout: 45000,
  // Send the httpOnly auth cookies with every request (the secure path; the JWT
  // is no longer kept in localStorage where XSS could read it).
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// "authed" is a NON-sensitive marker (not the token) telling the client a session
// likely exists, so it knows whether to attempt /me and silent refresh on 401.
const AUTH_FLAG = "authed";
// The CSRF token (double-submit). Safe to keep in JS — security comes from a
// cross-site attacker being unable to read it. Captured from login/refresh bodies.
const CSRF_KEY = "csrf";
const MUTATING = ["post", "put", "patch", "delete"];

function storeCsrf(data: any) {
  if (typeof window !== "undefined" && data && typeof data === "object" && data.csrf_token) {
    localStorage.setItem(CSRF_KEY, data.csrf_token);
  }
}

client.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    // Backward-compat: send any legacy localStorage token as a Bearer header.
    // New logins don't store one — auth rides the httpOnly cookie.
    const legacy = localStorage.getItem("token");
    if (legacy) config.headers.Authorization = `Bearer ${legacy}`;
    // Double-submit CSRF header on mutating requests.
    if (MUTATING.includes((config.method || "get").toLowerCase())) {
      const csrf = localStorage.getItem(CSRF_KEY);
      if (csrf) config.headers["X-CSRF-Token"] = csrf;
    }
  }
  return config;
});

function clearSession() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  localStorage.removeItem(AUTH_FLAG);
  localStorage.removeItem(CSRF_KEY);
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

// On 401 for an apparently-authenticated user, try a one-shot silent refresh (uses
// the httpOnly refresh cookie) and retry the original request. Guests (no session
// marker) are left alone so public pages can handle their own 401s.
client.interceptors.response.use(
  (response) => {
    storeCsrf(response.data); // capture CSRF token from login/refresh bodies
    return response;
  },
  async (error) => {
    const original = error?.config;
    const status = error?.response?.status;
    const url: string = original?.url || "";
    const isAuthCall =
      url.includes("/auth/login") || url.includes("/auth/refresh") || url.includes("/auth/logout");

    if (
      status === 401 && original && !original._retry && !isAuthCall &&
      typeof window !== "undefined" &&
      (localStorage.getItem(AUTH_FLAG) || localStorage.getItem("token"))
    ) {
      original._retry = true;
      try {
        await client.post("/auth/refresh");
        return client(original); // retry with the refreshed access cookie
      } catch {
        clearSession();
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

// ── TYPES ───────────────────────────────────────────────────────
export interface StockQuote {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  change_pct: number;
  prev_close?: number;
  volume: number;
  market_cap: number | null;
  day_high?: number;
  day_low?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
}

export interface Fundamentals {
  ticker: string;
  pe_ratio: number | null;
  pb_ratio: number | null;
  ev_ebitda?: number | null;
  ps_ratio?: number | null;
  peg_ratio?: number | null;
  roe: number | null;
  roce?: number | null;
  roa?: number | null;
  net_margin?: number | null;
  operating_margin?: number | null;
  current_ratio?: number | null;
  quick_ratio?: number | null;
  debt_equity: number | null;
  interest_coverage?: number | null;
  revenue_growth: number | null;
  dividend_yield?: number | null;
  market_cap: number | null;
  book_value?: number | null;
  face_value?: number | null;
  sector: string | null;
  industry?: string | null;
  exchange?: string | null;
  factor_scores?: {
    momentum?: number;
    quality?: number;
    value?: number;
    growth?: number;
    low_volatility?: number;
    composite?: number;
  };
}

export interface ScreenerResult {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  change_pct: number;
  pe_ratio: number | null;
  pb_ratio: number | null;
  roe: number | null;
  revenue_growth: number | null;
  momentum_score: number | null;
  quality_score: number | null;
  value_score: number | null;
  growth_score: number | null;
  composite_score: number | null;
  market_cap: number | null;
}

export interface PortfolioSummary {
  id: number;
  name: string;
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  position_count: number;
}

export interface BacktestMetrics {
  total_return: number;
  annualised_return: number;
  benchmark_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
}

// ── STOCKS ──────────────────────────────────────────────────────
export const stocksApi = {
  getQuote: (ticker: string, refresh = false) =>
    client.get<StockQuote>(`/stocks/${ticker}/quote`, { params: { refresh } }).then((r) => r.data),

  getHistory: (ticker: string, period = "1y", refresh = false) =>
    client.get(`/stocks/${ticker}/history`, { params: { period, refresh } }).then((r) => r.data),

  getFundamentals: (ticker: string, refresh = false) =>
    client.get<Fundamentals>(`/stocks/${ticker}/fundamentals`, { params: { refresh } }).then((r) => r.data),

  getFactors: (ticker: string) =>
    client.get(`/stocks/${ticker}/factors`).then((r) => r.data),

  getTechnicals: (ticker: string) =>
    client.get(`/stocks/${ticker}/technicals`).then((r) => r.data),

  getBatchQuotes: (tickers: string[], refresh = false) =>
    client.get(`/stocks/batch/quotes`, { params: { tickers: tickers.join(","), refresh } }).then((r) => r.data),

  search: (query: string) =>
    client.get(`/stocks/search`, { params: { q: query } }).then((r) => r.data),
};

// ── SCREENER ────────────────────────────────────────────────────
// Cold-cache screener runs scrape screener.in + Yahoo per stock across the Nifty 500
// with rate-limit backoff, which can take well over the default 45s — give it room.
const SCREENER_TIMEOUT = { timeout: 120000 };

export const screenerApi = {
  screen: (filters: Record<string, any>) =>
    client.post<{ results: ScreenerResult[]; total: number; filtered: number }>("/screener", filters, SCREENER_TIMEOUT)
      .then((r) => r.data),

  getSectors: () => client.get<{ sectors: string[] }>("/screener/sectors").then((r) => r.data),

  getFactorDefinitions: () => client.get("/screener/factor-definitions").then((r) => r.data),
};

// ── PORTFOLIO ───────────────────────────────────────────────────
export const portfolioApi = {
  list: () => client.get<PortfolioSummary[]>("/portfolio").then((r) => r.data),

  create: (data: { name: string; currency?: string; benchmark?: string }) =>
    client.post("/portfolio", data).then((r) => r.data),

  get: (id: number, refresh = false) => client.get(`/portfolio/${id}`, { params: { refresh } }).then((r) => r.data),

  addPosition: (portfolioId: number, position: { ticker: string; quantity: number; avg_cost: number }) =>
    client.post(`/portfolio/${portfolioId}/positions`, position).then((r) => r.data),

  removePosition: (portfolioId: number, positionId: number) =>
    client.delete(`/portfolio/${portfolioId}/positions/${positionId}`).then((r) => r.data),

  getSectorAllocation: (portfolioId: number) =>
    client.get(`/portfolio/${portfolioId}/sector-allocation`).then((r) => r.data),

  delete: (id: number) =>
    client.delete(`/portfolio/${id}`).then((r) => r.data),

  getPerformance: (id: number, benchmark = "NIFTY50", period = "1y", refresh = false) =>
    client.get(`/portfolio/${id}/performance`, { params: { benchmark, period, refresh } }).then((r) => r.data),

  importPositions: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return client.post(`/portfolio/${id}/import`, form).then((r) => r.data);
  },

  // Export the valued portfolio as csv/xlsx/pdf and trigger a browser download.
  exportPortfolio: async (id: number, name: string, format: "csv" | "xlsx" | "pdf") => {
    const r = await client.get(`/portfolio/${id}/export`, {
      params: { format },
      responseType: "blob",
    });
    const safe = (name || "portfolio").replace(/[^a-zA-Z0-9_-]/g, "") || "portfolio";
    downloadBlob(r.data, `${safe}.${format}`);
  },

  getTaxReport: (id: number) =>
    client.get(`/portfolio/${id}/tax-report`).then((r) => r.data),
};

// Trigger a client-side download for a Blob response.
function downloadBlob(blob: Blob, filename: string) {
  if (typeof window === "undefined") return;
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

// ── BACKTEST ────────────────────────────────────────────────────
export const backtestApi = {
  run: (request: Record<string, any>) =>
    client.post("/backtest", request).then((r) => r.data),

  getStrategyTemplates: () => client.get("/backtest/strategies").then((r) => r.data),
};

// ── MACRO ───────────────────────────────────────────────────────
export const macroApi = {
  getDashboard: (refresh = false) => client.get("/macro", { params: { refresh } }).then((r) => r.data),
  getRegime: () => client.get("/macro/regime").then((r) => r.data),
  getIndicators: (refresh = false) => client.get("/macro", { params: { refresh } }).then((r) => r.data),
};

// ── AI ──────────────────────────────────────────────────────────
// LLM generation can be slow on self-hosted Ollama — give AI calls a longer timeout.
const AI_TIMEOUT = { timeout: 120000 };

export const aiApi = {
  chat: (data: { messages: Array<{ role: string; content: string }>; context_ticker?: string; provider?: string; model?: string; api_key?: string }) =>
    client.post("/ai/chat", data, AI_TIMEOUT).then((r) => r.data),

  generateReport: (ticker: string, reportType = "full") =>
    client.post(`/ai/report/${ticker}`, { ticker, report_type: reportType }, AI_TIMEOUT).then((r) => r.data),

  generateThesis: (ticker: string) =>
    client.post(`/ai/thesis/${ticker}`, undefined, AI_TIMEOUT).then((r) => r.data),

  earningsSummary: (ticker: string, period = "latest") =>
    client.post("/ai/earnings-summary", { ticker, period }, AI_TIMEOUT).then((r) => r.data),

  portfolioRiskNarrative: (portfolioData: Record<string, any>) =>
    client.post("/ai/portfolio-risk-narrative", portfolioData, AI_TIMEOUT).then((r) => r.data),

  getReport: (data: { ticker: string; report_type?: string }) =>
    client.post("/ai/report", data, AI_TIMEOUT).then((r) => r.data),

  getEarningsSummary: (data: { ticker: string; period?: string }) =>
    client.post("/ai/earnings-summary", data, AI_TIMEOUT).then((r) => r.data),

  // ── RAG (Phase D) ──
  semanticSearch: (query: string, k = 5, kind?: string) =>
    client.post("/ai/semantic-search", { query, k, kind }).then((r) => r.data),

  ask: (query: string, k?: number) =>
    client.post("/ai/ask", { query, k }, AI_TIMEOUT).then((r) => r.data),

  ragStatus: () => client.get("/ai/rag/status").then((r) => r.data),

  // Conversation history
  listConversations: () => client.get("/ai/conversations").then((r) => r.data),
  createConversation: (title?: string) =>
    client.post("/ai/conversations", { title }).then((r) => r.data),
  getConversation: (id: number) =>
    client.get(`/ai/conversations/${id}`).then((r) => r.data),
  sendConversationMessage: (id: number, content: string, useRag = true) =>
    client.post(`/ai/conversations/${id}/messages`, { content, use_rag: useRag }, AI_TIMEOUT).then((r) => r.data),
  deleteConversation: (id: number) =>
    client.delete(`/ai/conversations/${id}`).then((r) => r.data),
};

// ── DASHBOARD ────────────────────────────────────────────────────
export const dashboardApi = {
  getMarketSummary: (refresh = false) =>
    client.get("/dashboard/market-summary", { params: { refresh } }).then((r) => r.data),

  getTopMovers: (refresh = false) =>
    client.get("/dashboard/top-gainers-losers", { params: { refresh } }).then((r) => r.data),

  getTopGainersLosers: (refresh = false) =>
    client.get("/dashboard/top-gainers-losers", { params: { refresh } }).then((r) => r.data),

  getSectorPerformance: (refresh = false) =>
    client.get("/dashboard/sector-performance", { params: { refresh } }).then((r) => r.data),

  getFactorSignals: (refresh = false) =>
    client.get("/dashboard/factor-signals", { params: { refresh } }).then((r) => r.data),

  getUniverseOverview: (refresh = false) =>
    client.get("/dashboard/universe-overview", { params: { refresh } }).then((r) => r.data),
};

// ── NEWS ──────────────────────────────────────────────────────────
export const newsApi = {
  getNews: () =>
    client.get("/news").then((r) => r.data),

  getTickerSentiment: (ticker: string) =>
    client.get(`/news/sentiment/${ticker}`).then((r) => r.data),
};

// ── EARNINGS ──────────────────────────────────────────────────────
export const earningsApi = {
  getCalendar: () =>
    client.get("/earnings/calendar").then((r) => r.data),

  getHistory: (ticker: string) =>
    client.get(`/earnings/${ticker}/history`).then((r) => r.data),
};

// ── QUANT LAB ─────────────────────────────────────────────────────
// The factor lab scores up to 500 names and can run optimisation / Monte-Carlo,
// so give these calls the same generous timeout as the screener.
const QUANTLAB_TIMEOUT = { timeout: 120000 };

export const quantLabApi = {
  scoreUniverse: (request: Record<string, any>) =>
    client.post("/quant-lab/score", request).then((r) => r.data),

  getFactorDefinitions: () =>
    client.get<Record<string, { label: string; description: string; family: string }>>(
      "/quant-lab/factor-definitions",
    ).then((r) => r.data),

  score: (body: { name: string; factor_weights: Record<string, number>; universe: string }) =>
    client.post<{ model_name: string; factors: string[]; weights: Record<string, number>; count: number; results: any[] }>(
      "/quant-lab/score", body, QUANTLAB_TIMEOUT,
    ).then((r) => r.data),

  optimize: (body: { name: string; factor_weights: Record<string, number>; universe: string }) =>
    client.post<{ model_name: string; holdings: any[]; metrics: Record<string, number> }>(
      "/quant-lab/optimize", body, QUANTLAB_TIMEOUT,
    ).then((r) => r.data),

  monteCarlo: (body: { name: string; factor_weights: Record<string, number>; universe: string }) =>
    client.post<{ projected_return_pct: Record<string, number>; prob_loss_pct: number; expected_value: number; simulations: number; horizon_days: number }>(
      "/quant-lab/monte-carlo", body, QUANTLAB_TIMEOUT,
    ).then((r) => r.data),
};

// ── STRATEGY BUILDER ──────────────────────────────────────────────
export const strategyBuilderApi = {
  backtest: (request: Record<string, any>) =>
    client.post("/strategy-builder/backtest", request).then((r) => r.data),

  getRuleTemplates: () =>
    client.get("/strategy-builder/rule-templates").then((r) => r.data),
};

// ── WATCHLISTS ────────────────────────────────────────────────────
export const watchlistsApi = {
  create: (data: { name: string; tickers?: string[] }) =>
    client.post("/watchlists", data).then((r) => r.data),

  list: () =>
    client.get("/watchlists").then((r) => r.data),

  get: (id: number, refresh = false) =>
    client.get(`/watchlists/${id}`, { params: { refresh } }).then((r) => r.data),

  updateTickers: (id: number, tickers: string[]) =>
    client.put(`/watchlists/${id}/tickers`, tickers).then((r) => r.data),

  delete: (id: number) =>
    client.delete(`/watchlists/${id}`).then((r) => r.data),

  getPerformance: (id: number, benchmark = "NIFTY50", period = "1y") =>
    client.get(`/watchlists/${id}/performance`, { params: { benchmark, period } }).then((r) => r.data),
};

// ── ALERTS ────────────────────────────────────────────────────────
export const alertsApi = {
  create: (data: { ticker: string; condition_type: string; threshold: number }) =>
    client.post("/alerts", data).then((r) => r.data),

  list: () =>
    client.get("/alerts").then((r) => r.data),

  evaluate: () =>
    client.get("/alerts/evaluate").then((r) => r.data),

  delete: (id: number) =>
    client.delete(`/alerts/${id}`).then((r) => r.data),
};

// ── AUTH ──────────────────────────────────────────────────────────
export const authApi = {
  register: (data: Record<string, any>) =>
    client.post("/auth/register", data).then((r) => r.data),

  login: (data: URLSearchParams) =>
    client.post("/auth/login", data, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }).then((r) => r.data),

  refresh: () => client.post("/auth/refresh").then((r) => r.data),

  logout: () => client.post("/auth/logout").then((r) => r.data),

  me: () =>
    client.get("/auth/me").then((r) => r.data),

  forgotPassword: (email: string) =>
    client.post("/auth/forgot-password", { email }).then((r) => r.data),

  resetPassword: (token: string, new_password: string) =>
    client.post("/auth/reset-password", { token, new_password }).then((r) => r.data),

  sendVerification: () =>
    client.post("/auth/send-verification").then((r) => r.data),

  verifyEmail: (token: string) =>
    client.post("/auth/verify-email", { token }).then((r) => r.data),
};


// ── STOCK INSIGHT (consolidated — replaces 4+ sequential calls) ─────
export const insightApi = {
  getStockInsight: (ticker: string, includeAi = false, refresh = false) =>
    client.get(`/insight/${ticker}`, { params: { include_ai: includeAi, refresh } }).then((r) => r.data),
};

// ── MUTUAL FUNDS ──────────────────────────────────────────────────
export interface MFSearchResult {
  scheme_code: number;
  scheme_name: string;
  fund_house?: string | null;
  category?: string | null;
}

export const mfApi = {
  search: (q: string) =>
    client.get<{ query: string; count: number; results: MFSearchResult[] }>("/mf/search", { params: { q } })
      .then((r) => r.data),

  popular: () =>
    client.get<{ results: MFSearchResult[] }>("/mf/popular").then((r) => r.data),

  getScheme: (code: number, period = "3y") =>
    client.get(`/mf/${code}`, { params: { period } }).then((r) => r.data),

  getReturns: (code: number) =>
    client.get(`/mf/${code}/returns`).then((r) => r.data),

  getRisk: (code: number) =>
    client.get(`/mf/${code}/risk`).then((r) => r.data),

  sipCalculator: (body: { monthly_amount: number; years: number; expected_return?: number; annual_step_up?: number }) =>
    client.post("/mf/sip-calculator", body).then((r) => r.data),

  compare: (scheme_codes: number[]) =>
    client.post("/mf/compare", { scheme_codes }).then((r) => r.data),
};

// ── IPO ───────────────────────────────────────────────────────────
export interface IPOItem {
  id: string;
  company_name: string;
  symbol?: string | null;
  exchange: string;
  ipo_type: string;
  issue_size_cr?: number | null;
  price_band_low?: number | null;
  price_band_high?: number | null;
  lot_size?: number | null;
  open_date?: string | null;
  close_date?: string | null;
  listing_date?: string | null;
  listing_price?: number | null;
  current_price?: number | null;
  listing_gain_pct?: number | null;
  gmp?: number | null;
  gmp_pct?: number | null;
  subscription_times?: number | null;
  status: string;
}

export const ipoApi = {
  all: (refresh = false) => client.get<{ ipos: IPOItem[] }>("/ipo", { params: { refresh } }).then((r) => r.data),
  upcoming: () => client.get<{ ipos: IPOItem[] }>("/ipo/upcoming").then((r) => r.data),
  open: () => client.get<{ ipos: IPOItem[] }>("/ipo/open").then((r) => r.data),
  listed: (days = 60) => client.get<{ ipos: IPOItem[] }>("/ipo/listed", { params: { days } }).then((r) => r.data),
  sme: () => client.get<{ ipos: IPOItem[] }>("/ipo/sme").then((r) => r.data),
  calendar: (month?: string) => client.get("/ipo/calendar", { params: { month } }).then((r) => r.data),
};

// ── SIMULATOR (paper trading) ─────────────────────────────────────
export interface SimPortfolioRef {
  id: number;
  name: string;
  starting_capital: number;
  cash: number;
}

export interface SimHolding {
  ticker: string;
  name: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  invested: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  change_pct: number;
  weight_pct: number;
  source: string;
}

export interface SimPortfolioState {
  id: number;
  name: string;
  starting_capital: number;
  cash: number;
  invested: number;
  market_value: number;
  total_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  total_pnl_pct: number;
  holdings: SimHolding[];
  holdings_count: number;
  created_at: string;
}

export interface SimTransaction {
  id: number;
  ticker: string;
  side: string;
  quantity: number;
  price: number;
  fees: number;
  realized_pnl: number;
  timestamp: string;
}

export interface SimPerformance {
  starting_capital: number;
  current_value: number;
  total_return_pct: number;
  realized_pnl: number;
  unrealized_pnl: number;
  trades_total: number;
  sells_closed: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  best_trade: number;
  worst_trade: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  equity_curve: { date: string; value: number }[];
}

export const simulatorApi = {
  createPortfolio: (data: { name: string; starting_capital: number }) =>
    client.post<SimPortfolioRef>("/simulator/portfolio", data).then((r) => r.data),

  listPortfolios: () =>
    client.get<SimPortfolioRef[]>("/simulator/portfolios").then((r) => r.data),

  getPortfolio: (id: number) =>
    client.get<SimPortfolioState>(`/simulator/${id}/portfolio`).then((r) => r.data),

  trade: (id: number, data: { ticker: string; side: "BUY" | "SELL"; quantity: number; price?: number }) =>
    client.post<SimTransaction>(`/simulator/${id}/trade`, data).then((r) => r.data),

  getTrades: (id: number) =>
    client.get<SimTransaction[]>(`/simulator/${id}/trades`).then((r) => r.data),

  getPerformance: (id: number) =>
    client.get<SimPerformance>(`/simulator/${id}/performance`).then((r) => r.data),

  delete: (id: number) =>
    client.delete(`/simulator/${id}`).then((r) => r.data),
};

// ── INDICES ───────────────────────────────────────────────────────
export interface IndexQuote {
  name: string;
  symbol: string;
  group: string;
  last: number;
  change: number;
  change_pct: number;
  as_of?: string | null;
}

export interface IndexConstituent {
  ticker: string;
  name: string;
  price: number;
  change_pct: number;
  sector: string;
}

export interface IndexDetail extends IndexQuote {
  advancers: number;
  decliners: number;
  constituents: IndexConstituent[];
}

export const indicesApi = {
  all: (refresh = false) =>
    client.get<{ indices: IndexQuote[] }>("/dashboard/indices", { params: { refresh } }).then((r) => r.data),
  detail: (symbol: string, refresh = false) =>
    client.get<IndexDetail>("/dashboard/index", { params: { symbol, refresh } }).then((r) => r.data),
};

// ── SECTORS ───────────────────────────────────────────────────────
export interface SectorComponent {
  ticker: string;
  name: string;
  price: number;
  change_pct: number;
  composite_score: number | null;
}

export interface SectorPerf {
  name: string;
  change_pct: number;
  week_pct: number | null;
  month_pct: number | null;
  avg_pe: number | null;
  avg_roe: number | null;
  momentum_score: number | null;
  composite_score: number | null;
  stock_count: number;
  advancers: number;
  decliners: number;
  top_gainer: SectorComponent | null;
  top_loser: SectorComponent | null;
  components: SectorComponent[];
}

export interface SectorsResponse {
  sectors: SectorPerf[];
  heatmap: Record<string, number>;
  sentiment: { bullish: number; neutral: number; bearish: number };
  top_gainers: SectorComponent[];
  top_losers: SectorComponent[];
}

export const sectorsApi = {
  getPerformance: (refresh = false) =>
    client.get<SectorsResponse>("/sectors/performance", { params: { refresh } }).then((r) => r.data),
};

// ── COMPARE (multi-asset) ─────────────────────────────────────────
export interface CompareScores {
  momentum: number | null;
  quality: number | null;
  value: number | null;
  growth: number | null;
  low_vol: number | null;
  composite: number | null;
}

export interface CompareAsset {
  ticker: string;
  name: string;
  sector: string | null;
  price: number;
  change_pct: number;
  pe_ratio: number | null;
  pb_ratio: number | null;
  roe: number | null;
  dividend_yield: number | null;
  debt_equity: number | null;
  market_cap: number | null;
  returns_period: number | null;
  volatility: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  scores: CompareScores;
  spark: number[];
  source: string;
}

export interface BestPick {
  ticker: string | null;
  value: number | null;
  reason: string;
}

export interface CompareResponse {
  assets: CompareAsset[];
  radar: Array<Record<string, string | number>>;
  best_momentum: BestPick;
  best_quality: BestPick;
  best_value: BestPick;
  best_risk_adjusted: BestPick;
  best_return: BestPick;
  recommendation: string;
}

export const compareApi = {
  compareStocks: (tickers: string[], period = "1y") =>
    client.post<CompareResponse>("/compare/stocks", { tickers, period }).then((r) => r.data),
};

// MF refresh helpers
export const mfRefresh = {
  scheme: (code: number, period = "3y") =>
    client.get(`/mf/${code}`, { params: { period, refresh: true } }).then((r) => r.data),
};

export default client;
