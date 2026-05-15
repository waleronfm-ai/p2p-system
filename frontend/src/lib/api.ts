import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000' })

export interface ChartPoint {
  timestamp: string
  price: number
  snapshot_id: number
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
): Promise<ChartResponse> {
  const { data } = await api.get<ChartResponse>('/api/market/chart', {
    params: { exchange, pair, mode, hours },
  })
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
