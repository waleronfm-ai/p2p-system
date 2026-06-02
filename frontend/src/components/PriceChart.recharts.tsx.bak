import { useMemo, useEffect, useRef, useState } from 'react'
import {
  CartesianGrid,
  Customized,
  Legend,
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
  type Trade,
  fetchChartData,
  fetchOpportunities,
  fetchTrades,
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

function formatDateTime(iso: string): string {
  const d = parseUtc(iso)
  return new Intl.DateTimeFormat('ru-UA', {
    timeZone: TZ,
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
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

// ── Trade tooltip ──────────────────────────────────────────────────────────

interface TradeHoverState {
  trade: Trade
  clientX: number
  clientY: number
}

function TradeTooltip({ hovered }: { hovered: TradeHoverState }) {
  const { trade, clientX, clientY } = hovered
  const isBuy = trade.trade_type.toLowerCase() === 'buy'
  const typeLabel = isBuy ? 'Покупка' : 'Продажа'
  const typeColor = isBuy ? '#22C55E' : '#EF4444'

  const TOOLTIP_W = 220
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
        zIndex: 2001,
        pointerEvents: 'none',
        minWidth: 180,
        maxWidth: 220,
        boxShadow: '0 4px 20px rgba(0,0,0,0.55)',
        lineHeight: '1.65',
      }}
    >
      <div style={{ fontWeight: 600, color: typeColor, marginBottom: 4 }}>{typeLabel}</div>
      <div>
        Цена: <strong>{trade.price.toFixed(2)} ₴</strong>
      </div>
      <div>
        Объём: <strong>{trade.amount_usdt.toFixed(2)} USDT</strong>
      </div>
      <div>
        Сумма: <strong>{trade.amount_uah.toLocaleString('ru-UA', { maximumFractionDigits: 0 })} ₴</strong>
      </div>
      {trade.counterparty && <div>Контрагент: {trade.counterparty}</div>}
      {trade.bank && <div>Банк: {trade.bank}</div>}
      <div style={{ color: 'var(--muted)', fontSize: 11, marginTop: 4 }}>
        {formatDateTime(trade.executed_at)}
      </div>
    </div>
  )
}

// ── Band layer — p25/p75 percentile range ─────────────────────────────────

interface BandLayerProps {
  points: ChartPoint[]
}

function BandLayer({ points }: BandLayerProps) {
  const yScale = useYAxisScale() as ((v: number) => number) | undefined
  const plotArea = usePlotArea() as { x: number; y: number; width: number; height: number } | undefined

  if (!yScale || !plotArea || points.length < 2) return null

  const times = points.map((p) => parseUtc(p.timestamp).getTime())
  const minTime = times[0]
  const maxTime = times[times.length - 1]
  const timeRange = maxTime - minTime
  if (timeRange <= 0) return null

  const validPts = points.filter((p) => p.p25 != null && p.p75 != null)
  if (validPts.length < 2) return null

  const getX = (iso: string) => {
    const t = parseUtc(iso).getTime()
    return plotArea.x + ((t - minTime) / timeRange) * plotArea.width
  }

  const topPts = validPts.map((p) => [getX(p.timestamp), yScale(p.p75!)] as const)
  const botPts = [...validPts].reverse().map((p) => [getX(p.timestamp), yScale(p.p25!)] as const)

  const d = [
    `M ${topPts[0][0]} ${topPts[0][1]}`,
    ...topPts.slice(1).map(([x, y]) => `L ${x} ${y}`),
    ...botPts.map(([x, y]) => `L ${x} ${y}`),
    'Z',
  ].join(' ')

  return <path d={d} fill="var(--accent)" fillOpacity={0.12} stroke="none" />
}

// ── Trades layer — SVG markers for BUY/SELL trades ────────────────────────

interface TradesLayerProps {
  trades: Trade[]
  points: ChartPoint[]
  onHover: (state: TradeHoverState | null) => void
  mousePos: React.MutableRefObject<{ x: number; y: number }>
}

function TradesLayer({ trades, points, onHover, mousePos }: TradesLayerProps) {
  const yScale = useYAxisScale() as ((v: number) => number) | undefined
  const plotArea = usePlotArea() as { x: number; y: number; width: number; height: number } | undefined

  if (!yScale || !plotArea || points.length < 2) return null

  const times = points.map((p) => parseUtc(p.timestamp).getTime())
  const minTime = times[0]
  const maxTime = times[times.length - 1]
  const timeRange = maxTime - minTime
  if (timeRange <= 0) return null

  const MARKER_R = 7

  return (
    <g>
      {trades.map((trade) => {
        const t = parseUtc(trade.executed_at).getTime()
        if (t < minTime || t > maxTime) return null

        const cx = plotArea.x + ((t - minTime) / timeRange) * plotArea.width
        const cy = yScale(trade.price)
        if (!Number.isFinite(cy)) return null

        const isBuy = trade.trade_type.toLowerCase() === 'buy'
        const color = isBuy ? '#22C55E' : '#EF4444'
        // BUY marker sits below the price line, SELL sits above
        const markerCy = isBuy ? cy + MARKER_R + 3 : cy - MARKER_R - 3
        if (
          markerCy < plotArea.y - MARKER_R - 2 ||
          markerCy > plotArea.y + plotArea.height + MARKER_R + 2
        )
          return null

        return (
          <g
            key={trade.id}
            style={{ cursor: 'pointer' }}
            onMouseEnter={() =>
              onHover({ trade, clientX: mousePos.current.x, clientY: mousePos.current.y })
            }
            onMouseLeave={() => onHover(null)}
          >
            <circle
              cx={cx}
              cy={markerCy}
              r={MARKER_R}
              fill={color}
              fillOpacity={0.9}
              stroke="rgba(0,0,0,0.45)"
              strokeWidth={1}
            />
            <text
              x={cx}
              y={markerCy}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={8}
              fill="white"
              fontWeight="bold"
              style={{ pointerEvents: 'none', userSelect: 'none' }}
            >
              {isBuy ? '▲' : '▼'}
            </text>
          </g>
        )
      })}
    </g>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

const VOLUME_CHIPS = [
  { label: '1k', value: 1_000 },
  { label: '5k', value: 5_000 },
  { label: '25k', value: 25_000 },
  { label: '100k', value: 100_000 },
] as const

export function PriceChart() {
  const [exchange, setExchange] = useState<Exchange>('binance')
  const [mode, setMode] = useState<Mode>('buy')
  const [hours, setHours] = useState<Hours>(24)
  const [points, setPoints] = useState<ChartPoint[]>([])
  const [initialized, setInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [volumeInput, setVolumeInput] = useState('')
  const [volumeUah, setVolumeUah] = useState<number | undefined>(undefined)
  const [marketPoints, setMarketPoints] = useState<ChartPoint[]>([])

  const [opportunities, setOpportunities] = useState<OpportunitiesResponse | null>(null)
  const [hoveredOpp, setHoveredOpp] = useState<HoveredState | null>(null)

  const [trades, setTrades] = useState<Trade[]>([])
  const [hoveredTrade, setHoveredTrade] = useState<TradeHoverState | null>(null)

  // Track mouse position on chart wrapper to position tooltip reliably
  const mousePos = useRef({ x: 0, y: 0 })

  // Debounce raw input → resolved volumeUah (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      const n = parseFloat(volumeInput)
      setVolumeUah(volumeInput === '' || isNaN(n) ? undefined : n)
    }, 300)
    return () => clearTimeout(timer)
  }, [volumeInput])

  useEffect(() => {
    setInitialized(false)
    setError(null)

    const load = () => {
      fetchChartData(exchange, PAIR, mode, hours, volumeUah)
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
  }, [exchange, mode, hours, volumeUah])

  // Second series: unfiltered market data — only when volume filter is active
  useEffect(() => {
    if (volumeUah === undefined) {
      setMarketPoints([])
      return
    }
    const load = () => {
      fetchChartData(exchange, PAIR, mode, hours)
        .then((res) => setMarketPoints(res.points))
        .catch(() => setMarketPoints([]))
    }
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [exchange, mode, hours, volumeUah])

  useEffect(() => {
    const load = () => {
      fetchOpportunities(exchange, PAIR, volumeUah)
        .then(setOpportunities)
        .catch(() => {})
    }
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [exchange, volumeUah])

  // Trades: fetch once on mount + refresh every 60s, independent of filters
  useEffect(() => {
    const load = () => {
      fetchTrades(500).then(setTrades).catch(() => {})
    }
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [])

  const lastPrice = points.length > 0 ? points[points.length - 1].price : null

  const showMarket = volumeUah !== undefined && marketPoints.length > 0

  const marketById = useMemo(() => {
    const m = new Map<number, number>()
    for (const p of marketPoints) m.set(p.snapshot_id, p.price)
    return m
  }, [marketPoints])

  const chartData = points.map((p) => ({
    time: formatTime(p.timestamp, hours),
    price: p.price,
    marketPrice: marketById.get(p.snapshot_id),
  }))

  // Filter trades to visible time window + current exchange
  const visibleTrades = useMemo(() => {
    const cutoff = Date.now() - hours * 60 * 60 * 1000
    return trades.filter((t) => {
      const ts = parseUtc(t.executed_at).getTime()
      return ts >= cutoff && t.exchange.toLowerCase() === exchange.toLowerCase()
    })
  }, [trades, hours, exchange])

  const hasBuyTrades = visibleTrades.some((t) => t.trade_type.toLowerCase() === 'buy')
  const hasSellTrades = visibleTrades.some((t) => t.trade_type.toLowerCase() === 'sell')
  const hasTrades = hasBuyTrades || hasSellTrades

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

  // Extend Y domain to include opportunity prices, trade prices, and p25/p75 band
  const yDomain = useMemo<
    [
      number | 'auto' | ((v: number) => number),
      number | 'auto' | ((v: number) => number),
    ]
  >(() => {
    const extras: number[] = []
    if (showDots) extras.push(...opportunities!.opportunities.map((o) => o.price))
    if (visibleTrades.length > 0) extras.push(...visibleTrades.map((t) => t.price))
    for (const p of points) {
      if (p.p25 != null) extras.push(p.p25)
      if (p.p75 != null) extras.push(p.p75)
    }
    if (extras.length === 0) return ['auto', 'auto']
    const minExtra = Math.min(...extras)
    const maxExtra = Math.max(...extras)
    return [
      (dataMin: number) => +(Math.min(dataMin, minExtra) - 0.1).toFixed(2),
      (dataMax: number) => +(Math.max(dataMax, maxExtra) + 0.1).toFixed(2),
    ]
  }, [showDots, opportunities, visibleTrades, points])

  const showLegend = showMarket || hasTrades

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

            {/* Volume filter indicator */}
            {volumeUah !== undefined && (
              <div className="mt-1" style={{ color: 'var(--accent)', fontSize: 11 }}>
                Объём: {volumeUah.toLocaleString('ru-UA')} ₴
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

        {/* Volume filter row */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs" style={{ color: 'var(--muted)', whiteSpace: 'nowrap' }}>
            Мой объём:
          </span>
          <input
            type="number"
            min={1}
            placeholder="₴"
            value={volumeInput}
            onChange={(e) => setVolumeInput(e.target.value)}
            style={{
              width: 90,
              background: 'var(--surface)',
              color: 'var(--text)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              padding: '2px 8px',
              fontSize: 13,
              outline: 'none',
            }}
          />
          {VOLUME_CHIPS.map((chip) => {
            const active = volumeUah === chip.value
            return (
              <button
                key={chip.label}
                onClick={() => setVolumeInput(active ? '' : String(chip.value))}
                style={{
                  padding: '2px 10px',
                  fontSize: 12,
                  borderRadius: 6,
                  border: active ? 'none' : '1px solid var(--border)',
                  background: active ? 'var(--accent)' : 'transparent',
                  color: active ? '#000' : 'var(--muted)',
                  cursor: 'pointer',
                  fontWeight: active ? 600 : 400,
                  transition: 'background 0.15s, color 0.15s',
                }}
              >
                {chip.label}
              </button>
            )
          })}
          <button
            onClick={() => setVolumeInput('')}
            style={{
              padding: '2px 10px',
              fontSize: 12,
              borderRadius: 6,
              border: volumeUah === undefined ? 'none' : '1px solid var(--border)',
              background: volumeUah === undefined ? 'var(--accent)' : 'transparent',
              color: volumeUah === undefined ? '#000' : 'var(--muted)',
              cursor: 'pointer',
              fontWeight: volumeUah === undefined ? 600 : 400,
              transition: 'background 0.15s, color 0.15s',
            }}
          >
            Любой
          </button>
        </div>

        {/* Chart */}
        <div
          style={{ height: 280, flexShrink: 0 }}
          onMouseMove={(e) => {
            mousePos.current = { x: e.clientX, y: e.clientY }
          }}
          onMouseLeave={() => {
            setHoveredOpp(null)
            setHoveredTrade(null)
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
                {showLegend && (
                  <Legend
                    verticalAlign="top"
                    height={22}
                    wrapperStyle={{ fontSize: 11, paddingBottom: 2 }}
                    content={(props) => {
                      const payload = (props as { payload?: Array<{ value: string; color: string; payload?: { strokeDasharray?: string } }> }).payload ?? []
                      const entries: Array<{ label: string; color: string; dashed?: boolean; circle?: boolean }> = []
                      for (const p of payload) {
                        entries.push({ label: p.value, color: p.color, dashed: !!p.payload?.strokeDasharray })
                      }
                      if (hasBuyTrades) entries.push({ label: 'Покупки', color: '#22C55E', circle: true })
                      if (hasSellTrades) entries.push({ label: 'Продажи', color: '#EF4444', circle: true })
                      return (
                        <div style={{ display: 'flex', gap: 14, justifyContent: 'center', alignItems: 'center' }}>
                          {entries.map((e, i) => (
                            <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--muted)' }}>
                              {e.circle ? (
                                <svg width={12} height={12} style={{ flexShrink: 0 }}>
                                  <circle cx={6} cy={6} r={5} fill={e.color} fillOpacity={0.9} />
                                </svg>
                              ) : (
                                <svg width={16} height={4} style={{ flexShrink: 0 }}>
                                  <line
                                    x1={0} y1={2} x2={16} y2={2}
                                    stroke={e.color}
                                    strokeWidth={e.dashed ? 1 : 2}
                                    strokeDasharray={e.dashed ? '4 3' : undefined}
                                  />
                                </svg>
                              )}
                              {e.label}
                            </span>
                          ))}
                        </div>
                      )
                    }}
                  />
                )}

                <Tooltip
                  contentStyle={{
                    background: 'var(--surface)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 6,
                    color: 'var(--text)',
                    fontSize: 12,
                  }}
                  labelStyle={{ color: 'var(--muted)' }}
                  formatter={(value: number, name: string) => [
                    value.toFixed(4),
                    name === 'price' ? (showMarket ? 'Доступно мне' : 'Рынок') : 'Общий рынок',
                  ]}
                />
                <Customized
                  component={() => <BandLayer points={points} />}
                />

                <Line
                  type="monotone"
                  dataKey="price"
                  name={showMarket ? 'Доступно мне' : 'Рынок'}
                  stroke="var(--accent)"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: 'var(--accent)' }}
                />
                {showMarket && (
                  <Line
                    type="monotone"
                    dataKey="marketPrice"
                    name="Общий рынок"
                    stroke="var(--muted)"
                    strokeWidth={1}
                    strokeDasharray="4 3"
                    dot={false}
                    activeDot={false}
                    connectNulls
                  />
                )}

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

                {hasTrades && (
                  <Customized
                    component={() => (
                      <TradesLayer
                        trades={visibleTrades}
                        points={points}
                        onHover={setHoveredTrade}
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
      {hoveredTrade && <TradeTooltip hovered={hoveredTrade} />}
    </>
  )
}
