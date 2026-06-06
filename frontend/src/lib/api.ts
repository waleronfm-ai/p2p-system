import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
})

api.interceptors.request.use((config) => {
  const key = import.meta.env.VITE_API_KEY
  if (key) config.headers['X-Api-Key'] = key
  return config
})

export interface ChartPoint {
  timestamp: string
  price: number
  snapshot_id: number
  p25?: number | null
  p75?: number | null
}

export interface ChartResponse {
  exchange: string
  pair: string
  mode: string
  hours: number
  points: ChartPoint[]
  total_points: number
}

export async function fetchChartData(
  exchange: string,
  pair: string,
  mode: string,
  hours: number,
  volumeUah?: number,
): Promise<ChartResponse> {
  const params: Record<string, unknown> = { exchange, pair, mode, hours }
  if (volumeUah !== undefined) params.volume_uah = volumeUah
  const { data } = await api.get<ChartResponse>('/api/market/chart', { params })
  return data
}

export interface MakerInfo {
  nickname: string
  total_orders: number
  completion_rate: number
  is_merchant: boolean
  trust_level: 'expert' | 'normal' | 'novice' | 'unknown'
}

export interface BankInfo {
  name: string
  risk: 'safe' | 'caution' | 'avoid' | 'unknown'
}

export interface Order {
  price: number
  available_amount: number
  min_amount: number
  max_amount: number
  exchange: string
  pair: string
  mode: string
  maker: MakerInfo
  banks: BankInfo[]
  is_outlier: boolean
  snapshot_at: string
}

export async function fetchOrders(
  exchange: string,
  pair: string,
  mode: string,
  top: number,
): Promise<Order[]> {
  const { data } = await api.get<Order[]>('/api/market/orders', {
    params: { exchange, pair, mode, top },
  })
  return data
}

export async function fetchHealth(): Promise<boolean> {
  try {
    const { data } = await api.get('/api/health')
    return data?.status === 'ok'
  } catch {
    return false
  }
}

export interface Trade {
  id: number
  exchange: string
  order_id: string
  trade_type: string
  price: number
  amount_usdt: number
  amount_uah: number
  bank: string | null
  counterparty: string | null
  note: string | null
  executed_at: string
  created_at: string
}

export interface TradeCreate {
  exchange: string
  order_id: string
  trade_type: string
  price: number
  amount_usdt: number
  amount_uah: number
  bank?: string | null
  counterparty?: string | null
  note?: string | null
  executed_at: string
}

export async function fetchTrades(limit = 100, offset = 0): Promise<Trade[]> {
  const { data } = await api.get<Trade[]>('/api/trades', { params: { limit, offset } })
  return data
}

export async function createTrade(payload: TradeCreate): Promise<Trade> {
  const { data } = await api.post<Trade>('/api/trades', payload)
  return data
}

export async function deleteTrade(id: number): Promise<void> {
  await api.delete(`/api/trades/${id}`)
}

export interface TradeStats {
  total_trades: number
  buy_count: number
  sell_count: number
  total_usdt_bought: number
  total_usdt_sold: number
  total_uah_spent: number
  total_uah_received: number
  avg_buy_price: number | null
  avg_sell_price: number | null
  pnl_uah: number | null
}

export async function fetchTradeStats(from_dt?: string, to_dt?: string): Promise<TradeStats> {
  const params: Record<string, string> = {}
  if (from_dt) params.from_dt = from_dt
  if (to_dt) params.to_dt = to_dt
  const { data } = await api.get<TradeStats>('/api/trades/stats', { params })
  return data
}

export interface Position {
  usdt_balance: number
  avg_buy_price: number | null
  break_even: number | null
  realized_profit_uah: number | null
  total_trades: number
  buy_count: number
  sell_count: number
}

export async function fetchPosition(): Promise<Position> {
  const { data } = await api.get<Position>('/api/position')
  return data
}

// ---------------------------------------------------------------------------
// Opportunities (Шаг 7А/7Б)
// ---------------------------------------------------------------------------

export interface Opportunity {
  price: number
  available_amount: number
  min_amount: number
  max_amount: number
  exchange: string
  pair: string
  profit_per_usdt: number
  maker: MakerInfo
  banks: BankInfo[]
  snapshot_at: string
}

export interface OpportunitiesResponse {
  mode: 'entry' | 'exit'
  reference_price: number
  threshold_price: number
  opportunities: Opportunity[]
}

export async function fetchOpportunities(
  exchange: string,
  pair: string,
  volumeUah?: number,
): Promise<OpportunitiesResponse> {
  const params: Record<string, unknown> = { exchange, pair }
  if (volumeUah !== undefined) params.volume_uah = volumeUah
  const { data } = await api.get<OpportunitiesResponse>('/api/market/opportunities', { params })
  return data
}

// ---------------------------------------------------------------------------
// Chart aggregated — Шаг 8А/8Б
// ---------------------------------------------------------------------------

export interface ChartPointAgg {
  ts: number
  buy_price: number
  sell_price: number
  buy_p25?: number | null
  buy_p75?: number | null
  sell_p25?: number | null
  sell_p75?: number | null
}

export interface ChartAggResponse {
  timeframe: string
  points: ChartPointAgg[]
  insufficient_data: boolean
}

export interface TimeframesResponse {
  available: string[]
  disabled: string[]
}

export async function fetchChartAgg(
  exchange: string,
  pair: string,
  timeframe: string,
  volumeUah?: number,
): Promise<ChartAggResponse> {
  const params: Record<string, unknown> = { exchange, pair, timeframe }
  if (volumeUah !== undefined) params.volume_uah = volumeUah
  const { data } = await api.get<ChartAggResponse>('/api/market/chart', { params })
  return data
}

export async function fetchTimeframes(): Promise<TimeframesResponse> {
  const { data } = await api.get<TimeframesResponse>('/api/market/timeframes')
  return data
}

// ---------------------------------------------------------------------------
// Tracker Health (Шаг 8А)
// ---------------------------------------------------------------------------

export interface TrackerHealth {
  tracker_alive: boolean
  minutes_since_last_snapshot: number | null
  last_snapshot_at: string | null
  snapshots_last_hour: number
  orders_last_hour: number
  total_snapshots: number
  total_orders: number
  db_size_mb: number
  server_time: string
}

export async function fetchTrackerHealth(): Promise<TrackerHealth> {
  const { data } = await api.get<TrackerHealth>('/api/info/tracker-health')
  return data
}

// ---------------------------------------------------------------------------
// Trade Sessions (часть 2)
// ---------------------------------------------------------------------------

export interface SessionOut {
  id: number
  number: number
  start_capital_uah: number
  exchange: string
  status: string
  started_at: string
  closed_at: string | null
  close_sell_price: number | null
  realized_uah: number | null
  unrealized_uah: number | null
  usdt_remaining: number | null
  trade_count: number
}

export async function fetchActiveSession(): Promise<SessionOut | null> {
  const { data } = await api.get<SessionOut | null>('/api/sessions/active')
  return data
}

export async function startSession(
  start_capital_uah: number,
  exchange: string,
): Promise<SessionOut> {
  const { data } = await api.post<SessionOut>('/api/sessions/start', {
    start_capital_uah,
    exchange,
  })
  return data
}

export async function closeSession(id: number): Promise<SessionOut> {
  try {
    const { data } = await api.post<SessionOut>(`/api/sessions/${id}/close`)
    return data
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 503) {
      const detail = (err.response.data as { detail?: string })?.detail
      throw new Error(
        detail ?? 'Не удалось получить текущий курс. Попробуйте закрыть сессию через минуту.',
      )
    }
    throw err
  }
}
