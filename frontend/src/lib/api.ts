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

export async function fetchHealth(): Promise<boolean> {
  try {
    const { data } = await api.get('/api/health')
    return data?.status === 'ok'
  } catch {
    return false
  }
}
