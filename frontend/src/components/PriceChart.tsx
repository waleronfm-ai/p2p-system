import { useMemo, useEffect, useRef, useState } from 'react'
import {
  CartesianGrid,
  Customized,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  usePlotArea,
  useYAxisScale,
} from 'recharts'
import {
  type ChartPoint,
  type Opportunity,
  type OpportunitiesResponse,
  fetchChartData,
  fetchOpportunities,
} from '../lib/api'

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

const TRUST_SYMBOL: Record<string, string> = {
  expert: '★',
  normal: '·',
  novice: '!',
  unknown: '?',
}

function dotRadius(profit: number, maxProfit: number): number {
  if (maxProfit <= 0) return 5
  return Math.max(4, Math.min(10, 4 + (Math.abs(profit) / maxProfit) * 6))
}

// ── Opportunity tooltip ────────────────────────────────────────────────────

interface HoveredState {
  opp: Opportunity
  clientX: number
  clientY: number
}

function OppTooltip({ hovered }: { hovered: HoveredState }) {
  const { opp, clientX, clientY } = hovered
  const bankNames = opp.banks.map((b) => b.name).join(', ') || '—'
  const profitSign = opp.profit_per_usdt >= 0 ? '+' : ''
  const sym = TRUST_SYMBOL[opp.maker.trust_level] ?? '?'
  const levelName = opp.maker.trust_level.toUpperCase()
  const profitColor = opp.profit_per_usdt >= 0 ? '#22C55E' : '#EF4444'

  const TOOLTIP_W = 260
  const left =
    clientX + 14 + TOOLTIP_W > window.innerWidth ? clientX - TOOLTIP_W - 14 : clientX + 14

  return (
    <div
      style={{
        position: 'fixed',
        left,
        top: clientY - 14,
        background: 'var(--surface)',
        border: '1px solid rgba(255,255,255,0.13)',
        borderRadius: 8,
        padding: '10px 14px',
        fontSize: 12,
        color: 'var(--text)',
        zIndex: 2000,
        pointerEvents: 'none',
        minWidth: 200,
        maxWidth: 260,
        boxShadow: '0 4px 20px rgba(0,0,0,0.55)',
        lineHeight: '1.65',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 2 }}>
        {opp.maker.nickname} {sym}
        {opp.maker.is_merchant ? ' ⊕' : ''}
      </div>
      <div style={{ color: 'var(--muted)', fontSize: 11, marginBottom: 6 }}>
        {levelName} · {opp.maker.total_orders.toLocaleString('ru')} сделок ·{' '}
        {opp.maker.completion_rate.toFixed(1)}%
      </div>
      <div>
        Цена: <strong>{opp.price.toFixed(2)} ₴</strong>
      </div>
      <div>
        Объём: {opp.available_amount.toLocaleString('ru', { maximumFractionDigits: 0 })} USDT
      </div>
      <div>
        Лимиты: {opp.min_amount.toLocaleString('ru', { maximumFractionDigits: 0 })}–
        {opp.max_amount.toLocaleString('ru', { maximumFractionDigits: 0 })} ₴
      </div>
      <div>Банки: {bankNames}</div>
      <div style={{ marginTop: 6, fontWeight: 600, color: profitColor }}>
        {profitSign}
        {opp.profit_per_usdt.toFixed(2)} ₴/USDT
      </div>
    </div>
  )
}

// ── Dots layer — uses Recharts v3 hooks to get scale + plot area ──────────

interface DotsLayerProps {
  opportunities: OpportunitiesResponse
  dotColor: string
  maxProfit: number
  onHover: (state: HoveredState | null) => void
  mousePos: React.MutableRefObject<{ x: number; y: number }>
}

function DotsLayer({ opportunities, dotColor, maxProfit, onHover, mousePos }: DotsLayerProps) {
  // Recharts v3 hooks — work inside the Recharts chart context tree
  const yScale = useYAxisScale() as ((v: number) => number) | undefined
  const plotArea = usePlotArea() as { x: number; y: number; width: number; height: number } | undefined

  if (!yScale || !plotArea) return null

  const cx = plotArea.x + plotArea.width  // rightmost edge of the plot area

  return (
    <g>
      {opportunities.opportunities.map((opp, i) => {
        const cy = yScale(opp.price)
        if (!Number.isFinite(cy)) return null

        // Skip dots outside the visible plot area
        if (cy < plotArea.y - 2 || cy > plotArea.y + plotArea.height + 2) return null

        const r = dotRadius(opp.profit_per_usdt, maxProfit)
        return (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={r}
            fill={dotColor}
            fillOpacity={0.9}
            stroke="rgba(0,0,0,0.3)"
            strokeWidth={1}
            style={{ cursor: 'pointer' }}
            onMouseEnter={() =>
              onHover({ opp, clientX: mousePos.current.x, clientY: mousePos.current.y })
            }
            onMouseLeave={() => onHover(null)}
          />
        )
      })}
    </g>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export function PriceChart() {
  const [exchange, setExchange] = useState<Exchange>('binance')
  const [mode, setMode] = useState<Mode>('buy')
  const [hours, setHours] = useState<Hours>(24)
  const [points, setPoints] = useState<ChartPoint[]>([])
  const [initialized, setInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [opportunities, setOpportunities] = useState<OpportunitiesResponse | null>(null)
  const [hoveredOpp, setHoveredOpp] = useState<HoveredState | null>(null)

  // Track mouse position on chart wrapper to position tooltip reliably
  const mousePos = useRef({ x: 0, y: 0 })

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

  useEffect(() => {
    const load = () => {
      fetchOpportunities(exchange, PAIR)
        .then(setOpportunities)
        .catch(() => {})
    }
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [exchange])

  const lastPrice = points.length > 0 ? points[points.length - 1].price : null

  const chartData = points.map((p) => ({
    time: formatTime(p.timestamp, hours),
    price: p.price,
  }))

  // Show opportunity dots only when chart mode is compatible with opportunity mode
  const showDots =
    initialized &&
    !error &&
    chartData.length > 0 &&
    opportunities !== null &&
    opportunities.opportunities.length > 0 &&
    ((mode === 'buy' && opportunities.mode === 'entry') ||
      (mode === 'sell' && opportunities.mode === 'exit'))

  const dotColor = opportunities?.mode === 'exit' ? '#22C55E' : '#F7A600'
  const maxProfit = showDots
    ? Math.max(...opportunities!.opportunities.map((o) => Math.abs(o.profit_per_usdt)))
    : 0

  // Extend Y domain to include opportunity prices so dots appear inside the chart
  const yDomain = useMemo<
    [
      number | 'auto' | ((v: number) => number),
      number | 'auto' | ((v: number) => number),
    ]
  >(() => {
    if (!showDots) return ['auto', 'auto']
    const opps = opportunities!.opportunities
    const minOpp = Math.min(...opps.map((o) => o.price))
    const maxOpp = Math.max(...opps.map((o) => o.price))
    return [
      (dataMin: number) => +(Math.min(dataMin, minOpp) - 0.1).toFixed(2),
      (dataMax: number) => +(Math.max(dataMax, maxOpp) + 0.1).toFixed(2),
    ]
  }, [showDots, opportunities])

  return (
    <>
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

            {/* Mode indicator */}
            {opportunities && (
              <div className="mt-1.5 flex flex-col gap-0">
                <span className="text-xs" style={{ color: 'var(--muted)' }}>
                  Режим: {opportunities.mode === 'entry' ? 'вход' : 'выход'}
                </span>
                <span className="text-xs" style={{ color: 'var(--muted)', opacity: 0.6 }}>
                  Порог: {opportunities.threshold_price.toFixed(2)} ₴
                </span>
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
        <div
          style={{ height: 280, flexShrink: 0 }}
          onMouseMove={(e) => {
            mousePos.current = { x: e.clientX, y: e.clientY }
          }}
        >
          {!initialized && (
            <div
              className="flex items-center justify-center h-full text-sm"
              style={{ color: 'var(--muted)' }}
            >
              Загрузка…
            </div>
          )}
          {initialized && error && (
            <div
              className="flex items-center justify-center h-full text-sm"
              style={{ color: 'var(--red)' }}
            >
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
                  domain={yDomain}
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

                {showDots && (
                  <Customized
                    component={() => (
                      <DotsLayer
                        opportunities={opportunities!}
                        dotColor={dotColor}
                        maxProfit={maxProfit}
                        onHover={setHoveredOpp}
                        mousePos={mousePos}
                      />
                    )}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          )}
          {initialized && !error && chartData.length === 0 && (
            <div
              className="flex items-center justify-center h-full text-sm"
              style={{ color: 'var(--muted)' }}
            >
              Нет данных за выбранный период
            </div>
          )}
        </div>
      </div>

      {hoveredOpp && <OppTooltip hovered={hoveredOpp} />}
    </>
  )
}
