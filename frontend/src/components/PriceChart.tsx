import { useCallback, useEffect, useRef, useState } from 'react'
import {
  createChart,
  createSeriesMarkers,
  CrosshairMode,
  LineSeries,
  LineType,
} from 'lightweight-charts'
import {
  fetchChartAgg,
  fetchTimeframes,
  fetchTrades,
  type ChartPointAgg,
  type Trade,
} from '../lib/api'

type Exchange = 'binance' | 'bybit'
type Timeframe = '24h' | '7d' | '1m' | '3m' | '6m' | '1y'

const PAIR = 'USDT/UAH'
const TZ   = 'Europe/Kyiv'

const ALL_TIMEFRAMES: Timeframe[] = ['24h', '7d', '1m', '3m', '6m', '1y']

const TF_LABELS: Record<Timeframe, string> = {
  '24h': '24Ч', '7d': '7Д', '1m': '1М', '3m': '3М', '6m': '6М', '1y': '1Г',
}

const TF_HOURS: Record<Timeframe, number> = {
  '24h': 24, '7d': 168, '1m': 720, '3m': 2160, '6m': 4320, '1y': 8760,
}

const VOLUME_CHIPS = [
  { label: '1к',   value: 1_000 },
  { label: '5к',   value: 5_000 },
  { label: '25к',  value: 25_000 },
  { label: '100к', value: 100_000 },
] as const

function fmtKyiv(ts: number, short = true): string {
  const d = new Date(ts * 1000)
  if (short) {
    return new Intl.DateTimeFormat('ru-UA', {
      timeZone: TZ, hour: '2-digit', minute: '2-digit',
    }).format(d)
  }
  return new Intl.DateTimeFormat('ru-UA', {
    timeZone: TZ, day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).format(d)
}

function toUnixSec(iso: string): number {
  const s = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z'
  return Math.floor(new Date(s).getTime() / 1000)
}

const selectClass =
  'rounded px-2 py-1 text-sm border focus:outline-none focus:ring-1 focus:ring-[var(--accent)]'
const selectStyle = {
  background: 'var(--background)',
  color: 'var(--text)',
  borderColor: 'rgba(255,255,255,0.12)',
}

// ── Chip button helper ────────────────────────────────────────────────────────
function Chip({
  label,
  active,
  disabled,
  title,
  onClick,
}: {
  label: string
  active: boolean
  disabled?: boolean
  title?: string
  onClick?: () => void
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      title={title}
      style={{
        padding: '2px 8px',
        fontSize: 11,
        borderRadius: 6,
        border: active && !disabled ? 'none' : '1px solid rgba(255,255,255,0.12)',
        background: active && !disabled ? 'var(--accent)' : 'transparent',
        color: disabled
          ? 'rgba(255,255,255,0.2)'
          : active
            ? '#000'
            : 'var(--muted)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontWeight: active && !disabled ? 600 : 400,
        transition: 'background 0.15s, color 0.15s',
      }}
    >
      {label}
    </button>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef   = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const buyRef     = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sellRef    = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersRef = useRef<any>(null)       // createSeriesMarkers plugin
  const tradesRef  = useRef<Trade[]>([])     // текущие сделки (для crosshairMoved)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const [exchange,  setExchange]  = useState<Exchange>('binance')
  const [timeframe, setTimeframe] = useState<Timeframe>('24h')
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)
  const [noData,    setNoData]    = useState(false)
  const [lastBuy,   setLastBuy]   = useState<number | null>(null)
  const [lastSell,  setLastSell]  = useState<number | null>(null)
  const [available, setAvailable] = useState<string[]>([])
  const [disabled,  setDisabled]  = useState<string[]>([])

  // Тумблеры слоёв
  const [showTrades, setShowTrades] = useState(true)

  // Фильтр объёма (дефолт 5k ₴ — для чистоты графика)
  const [volumeChip, setVolumeChip] = useState<number | null>(5_000)

  // Сделки в state (для эффекта маркеров)
  const [trades, setTrades] = useState<Trade[]>([])

  // ── Создание графика (один раз при монтировании) ─────────────────────────
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      height: 400,
      layout: {
        background: { color: '#0E0E10' },
        textColor: '#E8E8EC',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.05)' },
        horzLines: { color: 'rgba(255,255,255,0.05)' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.1)',
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: number) => fmtKyiv(time, true),
      },
      localization: {
        locale: 'ru-UA',
        timeFormatter: (ts: number) => fmtKyiv(ts, false),
      },
    })

    const buy = chart.addSeries(LineSeries, {
      color: '#EF4444',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceScaleId: 'right',
      title: 'Покупка',
    })

    const sell = chart.addSeries(LineSeries, {
      color: '#F7A600',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceScaleId: 'right',
      title: 'Продажа',
    })

    // Плагин маркеров на серии покупки
    const markers = createSeriesMarkers(buy, [])
    markersRef.current = markers

    // Тултип при наведении на маркер через hoveredObjectId
    chart.subscribeCrosshairMove((params) => {
      if (!tooltipRef.current) return

      const markerId = params.hoveredObjectId
      if (!markerId || !params.point) {
        tooltipRef.current.style.display = 'none'
        return
      }

      const trade = tradesRef.current.find((t) => String(t.id) === String(markerId))
      if (!trade) {
        tooltipRef.current.style.display = 'none'
        return
      }

      const isBuy    = trade.trade_type === 'BUY'
      const color    = isBuy ? '#22C55E' : '#EF4444'
      const typeLabel = isBuy ? 'Покупка' : 'Продажа'
      const dateStr   = fmtKyiv(toUnixSec(trade.executed_at), false)
      const uahStr    = trade.amount_uah.toLocaleString('ru-UA', { maximumFractionDigits: 0 })

      tooltipRef.current.innerHTML = [
        `<div style="font-weight:600;color:${color};margin-bottom:4px">${typeLabel}</div>`,
        `<div>Цена: <strong>${trade.price.toFixed(2)} ₴</strong></div>`,
        `<div>Объём: <strong>${trade.amount_usdt.toFixed(2)} USDT</strong></div>`,
        `<div>Сумма: <strong>${uahStr} ₴</strong></div>`,
        trade.bank ? `<div>Банк: ${trade.bank}</div>` : '',
        `<div style="color:var(--muted);font-size:11px;margin-top:4px">${dateStr}</div>`,
      ].join('')

      const containerW = containerRef.current?.clientWidth ?? 400
      const tooltipW   = 220
      let left = params.point.x + 14
      if (left + tooltipW > containerW) left = params.point.x - tooltipW - 14
      tooltipRef.current.style.left = `${left}px`
      tooltipRef.current.style.top  = `${Math.max(0, params.point.y - 50)}px`
      tooltipRef.current.style.display = 'block'
    })

    chartRef.current = chart
    buyRef.current   = buy
    sellRef.current  = sell

    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (w) chart.applyOptions({ width: w })
    })
    observer.observe(containerRef.current)

    return () => {
      observer.disconnect()
      chart.remove()
      chartRef.current  = null
      buyRef.current    = null
      sellRef.current   = null
      markersRef.current = null
    }
  }, [])

  // ── Подача данных в серии ─────────────────────────────────────────────────
  const feedSeries = useCallback((points: ChartPointAgg[]) => {
    if (!buyRef.current || !sellRef.current) return

    if (points.length === 0) {
      buyRef.current.setData([])
      sellRef.current.setData([])
      setLastBuy(null)
      setLastSell(null)
      return
    }

    buyRef.current.setData(points.map((p) => ({ time: p.ts, value: p.buy_price })))
    sellRef.current.setData(points.map((p) => ({ time: p.ts, value: p.sell_price })))

    const last = points[points.length - 1]
    setLastBuy(last.buy_price)
    setLastSell(last.sell_price)
  }, [])

  // ── Загрузка данных графика ───────────────────────────────────────────────
  const loadChart = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchChartAgg(exchange, PAIR, timeframe, volumeChip ?? undefined)
      .then((res) => {
        setNoData(res.insufficient_data)
        feedSeries(res.insufficient_data ? [] : res.points)
        setLoading(false)
      })
      .catch(() => {
        setError('Ошибка загрузки данных')
        feedSeries([])
        setLoading(false)
      })
  }, [exchange, timeframe, volumeChip, feedSeries])

  useEffect(() => {
    loadChart()
    const id = setInterval(loadChart, 60_000)
    return () => clearInterval(id)
  }, [loadChart])

  // ── Загрузка доступных таймфреймов ───────────────────────────────────────
  useEffect(() => {
    fetchTimeframes()
      .then((res) => {
        setAvailable(res.available)
        setDisabled(res.disabled)
      })
      .catch(() => {})
  }, [exchange])

  // ── Загрузка сделок ───────────────────────────────────────────────────────
  useEffect(() => {
    const load = () => {
      fetchTrades(500, 0)
        .then((t) => {
          tradesRef.current = t   // обновляем ref сразу (для crosshairMoved)
          setTrades(t)
        })
        .catch(() => {})
    }
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [exchange])

  // ── Применение маркеров сделок ────────────────────────────────────────────
  useEffect(() => {
    if (!markersRef.current) return

    if (!showTrades) {
      markersRef.current.setMarkers([])
      return
    }

    const cutoffSec = Math.floor(Date.now() / 1000) - TF_HOURS[timeframe] * 3600
    const markers = trades
      .filter((t) =>
        t.exchange.toLowerCase() === exchange.toLowerCase() &&
        toUnixSec(t.executed_at) >= cutoffSec,
      )
      .map((t) => ({
        time: toUnixSec(t.executed_at),
        position: 'atPriceMiddle' as const,
        shape: (t.trade_type === 'BUY' ? 'arrowUp' : 'arrowDown') as const,
        color: t.trade_type === 'BUY' ? '#22C55E' : '#EF4444',
        price: t.price,
        text: t.amount_usdt.toFixed(0),
        id: String(t.id),
        size: 1.5,
      }))
      .sort((a, b) => a.time - b.time)  // lwc требует сортировку по времени

    markersRef.current.setMarkers(markers)
  }, [trades, showTrades, exchange, timeframe])

  // ── Рендер ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-3">

      {/* Заголовок + цены + управление */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <div className="font-bold text-base" style={{ color: 'var(--text)' }}>
            USDT / UAH
          </div>
          <div className="flex gap-4 mt-0.5 items-baseline">
            {lastBuy != null && (
              <span className="text-2xl font-semibold" style={{ color: '#EF4444' }}>
                {lastBuy.toFixed(2)}
              </span>
            )}
            {lastSell != null && (
              <span className="text-2xl font-semibold" style={{ color: '#F7A600' }}>
                {lastSell.toFixed(2)}
              </span>
            )}
            {lastBuy == null && lastSell == null && !loading && (
              <span className="text-sm" style={{ color: 'var(--muted)' }}>—</span>
            )}
          </div>
        </div>

        {/* Биржа + таймфреймы */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            className={selectClass}
            style={selectStyle}
            value={exchange}
            onChange={(e) => setExchange(e.target.value as Exchange)}
          >
            <option value="binance">Binance</option>
            <option value="bybit">Bybit</option>
          </select>

          <div className="flex gap-1">
            {ALL_TIMEFRAMES.map((tf) => {
              const isDis    = disabled.includes(tf) && !available.includes(tf)
              const isActive = timeframe === tf
              return (
                <button
                  key={tf}
                  disabled={isDis}
                  onClick={() => { if (!isDis) setTimeframe(tf) }}
                  title={isDis ? 'Накапливаем историю' : undefined}
                  style={{
                    padding: '3px 10px',
                    fontSize: 12,
                    fontWeight: isActive ? 600 : 400,
                    borderRadius: 6,
                    border: isActive ? 'none' : '1px solid rgba(255,255,255,0.12)',
                    background: isActive ? 'var(--accent)' : 'transparent',
                    color: isDis
                      ? 'rgba(255,255,255,0.2)'
                      : isActive
                        ? '#000'
                        : 'var(--muted)',
                    cursor: isDis ? 'not-allowed' : 'pointer',
                    transition: 'background 0.15s, color 0.15s',
                  }}
                >
                  {TF_LABELS[tf]}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Фильтр объёма + тумблеры слоёв */}
      <div className="flex items-center gap-3 flex-wrap">

        {/* Объём */}
        <div className="flex items-center gap-1">
          <span className="text-xs" style={{ color: 'var(--muted)', whiteSpace: 'nowrap' }}>
            Объём:
          </span>
          <Chip
            label="Любой"
            active={volumeChip === null}
            onClick={() => setVolumeChip(null)}
          />
          {VOLUME_CHIPS.map((c) => (
            <Chip
              key={c.label}
              label={c.label}
              active={volumeChip === c.value}
              onClick={() => setVolumeChip(c.value)}
            />
          ))}
        </div>

        {/* Разделитель */}
        <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.1)', flexShrink: 0 }} />

        {/* Слои */}
        <div className="flex items-center gap-1">
          <span className="text-xs" style={{ color: 'var(--muted)', whiteSpace: 'nowrap' }}>
            Слои:
          </span>
          <Chip
            label="Сделки"
            active={showTrades}
            onClick={() => setShowTrades((v) => !v)}
          />
          <Chip
            label="Коридор"
            active={false}
            disabled
            title="Скоро"
          />
          <Chip
            label="Возможности"
            active={false}
            disabled
            title="Скоро"
          />
        </div>
      </div>

      {/* Легенда */}
      <div className="flex gap-5 text-xs" style={{ color: 'var(--muted)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ display: 'inline-block', width: 18, height: 2, background: '#EF4444', borderRadius: 1 }} />
          Покупка
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ display: 'inline-block', width: 18, height: 2, background: '#F7A600', borderRadius: 1 }} />
          Продажа
        </span>
      </div>

      {/* Область графика */}
      <div style={{ position: 'relative', height: 400 }}>

        {/* Контейнер lightweight-charts */}
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

        {/* Тултип маркера сделки */}
        <div
          ref={tooltipRef}
          style={{
            display: 'none',
            position: 'absolute',
            background: 'var(--surface)',
            border: '1px solid rgba(255,255,255,0.13)',
            borderRadius: 8,
            padding: '10px 14px',
            fontSize: 12,
            color: 'var(--text)',
            zIndex: 100,
            pointerEvents: 'none',
            minWidth: 180,
            maxWidth: 220,
            boxShadow: '0 4px 20px rgba(0,0,0,0.55)',
            lineHeight: '1.65',
          }}
        />

        {/* Оверлей загрузки */}
        {loading && (
          <div style={overlayStyle}>
            <span style={{ color: 'var(--muted)', fontSize: 14 }}>Загрузка…</span>
          </div>
        )}

        {!loading && error && (
          <div style={overlayStyle}>
            <span style={{ color: 'var(--red)', fontSize: 14 }}>{error}</span>
          </div>
        )}

        {!loading && !error && noData && (
          <div style={overlayStyle}>
            <span style={{ color: 'var(--muted)', fontSize: 14 }}>
              Недостаточно данных для этого периода
            </span>
          </div>
        )}
      </div>

    </div>
  )
}

const overlayStyle: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: '#0E0E10',
  borderRadius: 4,
}
