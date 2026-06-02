import { useCallback, useEffect, useRef, useState } from 'react'
import { createChart, CrosshairMode, LineSeries } from 'lightweight-charts'
import {
  fetchChartAgg,
  fetchTimeframes,
  type ChartPointAgg,
} from '../lib/api'

type Exchange = 'binance' | 'bybit'
type Timeframe = '24h' | '7d' | '1m' | '3m' | '6m' | '1y'

const PAIR = 'USDT/UAH'
const TZ = 'Europe/Kyiv'

const ALL_TIMEFRAMES: Timeframe[] = ['24h', '7d', '1m', '3m', '6m', '1y']

const TF_LABELS: Record<Timeframe, string> = {
  '24h': '24Ч',
  '7d':  '7Д',
  '1m':  '1М',
  '3m':  '3М',
  '6m':  '6М',
  '1y':  '1Г',
}

// Europe/Kyiv — UTC+3 (постоянное летнее время с 2022)
function fmtKyiv(ts: number, short = true): string {
  const d = new Date(ts * 1000)
  if (short) {
    return new Intl.DateTimeFormat('ru-UA', {
      timeZone: TZ,
      hour: '2-digit',
      minute: '2-digit',
    }).format(d)
  }
  return new Intl.DateTimeFormat('ru-UA', {
    timeZone: TZ,
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}

const selectClass =
  'rounded px-2 py-1 text-sm border focus:outline-none focus:ring-1 focus:ring-[var(--accent)]'
const selectStyle = {
  background: 'var(--background)',
  color: 'var(--text)',
  borderColor: 'rgba(255,255,255,0.12)',
}

export function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef    = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const buyRef      = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sellRef     = useRef<any>(null)

  const [exchange,   setExchange]   = useState<Exchange>('binance')
  const [timeframe,  setTimeframe]  = useState<Timeframe>('24h')
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [noData,     setNoData]     = useState(false)
  const [lastBuy,    setLastBuy]    = useState<number | null>(null)
  const [lastSell,   setLastSell]   = useState<number | null>(null)
  const [available,  setAvailable]  = useState<string[]>([])
  const [disabled,   setDisabled]   = useState<string[]>([])

  // ── Создание графика (один раз при монтировании) ──────────────────────────
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
        // Отображаем время оси X в Europe/Kyiv
        tickMarkFormatter: (time: number) => fmtKyiv(time, true),
      },
      localization: {
        locale: 'ru-UA',
        // Время в тултипе кросскурсора — тоже Kyiv
        timeFormatter: (ts: number) => fmtKyiv(ts, false),
      },
    })

    const buy = chart.addSeries(LineSeries, {
      color: '#EF4444',
      lineWidth: 2,
      priceScaleId: 'right',
      title: 'Покупка',
    })

    const sell = chart.addSeries(LineSeries, {
      color: '#F7A600',
      lineWidth: 2,
      priceScaleId: 'right',
      title: 'Продажа',
    })

    chartRef.current = chart
    buyRef.current   = buy
    sellRef.current  = sell

    // Адаптивная ширина
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (w) chart.applyOptions({ width: w })
    })
    observer.observe(containerRef.current)

    return () => {
      observer.disconnect()
      chart.remove()
      chartRef.current = null
      buyRef.current   = null
      sellRef.current  = null
    }
  }, [])

  // ── Подача данных в серии ──────────────────────────────────────────────────
  const feedSeries = useCallback((points: ChartPointAgg[]) => {
    if (!buyRef.current || !sellRef.current) return

    if (points.length === 0) {
      buyRef.current.setData([])
      sellRef.current.setData([])
      setLastBuy(null)
      setLastSell(null)
      return
    }

    buyRef.current.setData(
      points.map((p) => ({ time: p.ts, value: p.buy_price })),
    )
    sellRef.current.setData(
      points.map((p) => ({ time: p.ts, value: p.sell_price })),
    )

    const last = points[points.length - 1]
    setLastBuy(last.buy_price)
    setLastSell(last.sell_price)
  }, [])

  // ── Загрузка данных графика ────────────────────────────────────────────────
  const loadChart = useCallback(() => {
    setLoading(true)
    setError(null)

    fetchChartAgg(exchange, PAIR, timeframe)
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
  }, [exchange, timeframe, feedSeries])

  useEffect(() => {
    loadChart()
    const id = setInterval(loadChart, 60_000)
    return () => clearInterval(id)
  }, [loadChart])

  // ── Загрузка доступных таймфреймов ────────────────────────────────────────
  useEffect(() => {
    fetchTimeframes()
      .then((res) => {
        setAvailable(res.available)
        setDisabled(res.disabled)
      })
      .catch(() => {})
  }, [exchange])

  // ── Рендер ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-3">

      {/* Заголовок + цены */}
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

        {/* Управление */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Биржа */}
          <select
            className={selectClass}
            style={selectStyle}
            value={exchange}
            onChange={(e) => setExchange(e.target.value as Exchange)}
          >
            <option value="binance">Binance</option>
            <option value="bybit">Bybit</option>
          </select>

          {/* Таймфреймы */}
          <div className="flex gap-1">
            {ALL_TIMEFRAMES.map((tf) => {
              const isDisabled = disabled.includes(tf) && !available.includes(tf)
              const isActive   = timeframe === tf
              return (
                <button
                  key={tf}
                  disabled={isDisabled}
                  onClick={() => { if (!isDisabled) setTimeframe(tf) }}
                  title={isDisabled ? 'Накапливаем историю' : undefined}
                  style={{
                    padding: '3px 10px',
                    fontSize: 12,
                    fontWeight: isActive ? 600 : 400,
                    borderRadius: 6,
                    border: isActive ? 'none' : '1px solid rgba(255,255,255,0.12)',
                    background: isActive ? 'var(--accent)' : 'transparent',
                    color: isDisabled
                      ? 'rgba(255,255,255,0.2)'
                      : isActive
                        ? '#000'
                        : 'var(--muted)',
                    cursor: isDisabled ? 'not-allowed' : 'pointer',
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

        {/* Контейнер lightweight-charts (всегда в DOM для ResizeObserver) */}
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

        {/* Оверлей: загрузка */}
        {loading && (
          <div style={overlayStyle}>
            <span style={{ color: 'var(--muted)', fontSize: 14 }}>Загрузка…</span>
          </div>
        )}

        {/* Оверлей: ошибка */}
        {!loading && error && (
          <div style={overlayStyle}>
            <span style={{ color: 'var(--red)', fontSize: 14 }}>{error}</span>
          </div>
        )}

        {/* Оверлей: недостаточно данных */}
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
