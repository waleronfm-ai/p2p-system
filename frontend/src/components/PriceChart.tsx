import { useEffect, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { type ChartPoint, fetchChartData } from '../lib/api'

type Exchange = 'binance' | 'bybit'
type Mode = 'buy' | 'sell'
type Hours = 1 | 6 | 24 | 168

const PAIR = 'USDT/UAH'
const TZ = 'Europe/Kyiv'

// API returns naive UTC datetimes without timezone suffix — append 'Z' so the browser
// treats them as UTC instead of local time.
function parseUtc(iso: string): Date {
  return new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
}

const selectClass =
  'rounded px-2 py-1 text-sm border focus:outline-none focus:ring-1 focus:ring-[var(--accent)]'
const selectStyle = {
  background: 'var(--background)',
  color: 'var(--text)',
  borderColor: 'rgba(255,255,255,0.12)',
}

function formatTime(iso: string, hours: Hours): string {
  const d = parseUtc(iso)
  if (hours <= 24) {
    return new Intl.DateTimeFormat('ru-UA', {
      timeZone: TZ,
      hour: '2-digit',
      minute: '2-digit',
    }).format(d)
  }
  return new Intl.DateTimeFormat('ru-UA', {
    timeZone: TZ,
    month: 'short',
    day: 'numeric',
  }).format(d)
}

export function PriceChart() {
  const [exchange, setExchange] = useState<Exchange>('binance')
  const [mode, setMode] = useState<Mode>('buy')
  const [hours, setHours] = useState<Hours>(24)
  const [points, setPoints] = useState<ChartPoint[]>([])
  const [initialized, setInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setInitialized(false)
    setError(null)

    const load = () => {
      fetchChartData(exchange, PAIR, mode, hours)
        .then((res) => {
          setPoints(res.points)
          setInitialized(true)
        })
        .catch(() => {
          setError('Нет данных')
          setInitialized(true)
        })
    }

    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [exchange, mode, hours])

  const lastPrice = points.length > 0 ? points[points.length - 1].price : null

  const chartData = points.map((p) => ({
    time: formatTime(p.timestamp, hours),
    price: p.price,
  }))

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <div className="font-bold text-base" style={{ color: 'var(--text)' }}>
            USDT / UAH
          </div>
          {lastPrice != null && (
            <div className="text-2xl font-semibold mt-0.5" style={{ color: 'var(--accent)' }}>
              {lastPrice.toFixed(2)}
            </div>
          )}
          {lastPrice == null && initialized && (
            <div className="text-sm mt-0.5" style={{ color: 'var(--muted)' }}>
              —
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex gap-2 flex-wrap">
          <select
            className={selectClass}
            style={selectStyle}
            value={exchange}
            onChange={(e) => setExchange(e.target.value as Exchange)}
          >
            <option value="binance">Binance</option>
            <option value="bybit">Bybit</option>
          </select>

          <select
            className={selectClass}
            style={selectStyle}
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}
          >
            <option value="buy">Купить USDT</option>
            <option value="sell">Продать USDT</option>
          </select>

          <select
            className={selectClass}
            style={selectStyle}
            value={hours}
            onChange={(e) => setHours(Number(e.target.value) as Hours)}
          >
            <option value={1}>1ч</option>
            <option value={6}>6ч</option>
            <option value={24}>24ч</option>
            <option value={168}>7д</option>
          </select>
        </div>
      </div>

      {/* Chart */}
      <div style={{ height: 280, flexShrink: 0 }}>
        {!initialized && (
          <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--muted)' }}>
            Загрузка…
          </div>
        )}
        {initialized && error && (
          <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--red)' }}>
            {error}
          </div>
        )}
        {initialized && !error && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
              <XAxis
                dataKey="time"
                tick={{ fill: 'var(--muted)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: 'var(--muted)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={52}
                tickFormatter={(v: number) => v.toFixed(1)}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--surface)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 6,
                  color: 'var(--text)',
                  fontSize: 12,
                }}
                labelStyle={{ color: 'var(--muted)' }}
                formatter={(value: number) => [value.toFixed(4), 'Цена']}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: 'var(--accent)' }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
        {initialized && !error && chartData.length === 0 && (
          <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--muted)' }}>
            Нет данных за выбранный период
          </div>
        )}
      </div>
    </div>
  )
}
