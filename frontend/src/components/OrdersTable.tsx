import { useEffect, useRef, useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table'
import { type Order, fetchOrders } from '../lib/api'

type Exchange = 'binance' | 'bybit'
type Mode = 'buy' | 'sell'
type Top = 10 | 15 | 25 | 50

const PAIR = 'USDT/UAH'
const REFRESH_MS = 30_000

const selectClass =
  'rounded px-2 py-1 text-xs border focus:outline-none focus:ring-1 focus:ring-[var(--accent)]'
const selectStyle = {
  background: 'var(--background)',
  color: 'var(--text)',
  borderColor: 'rgba(255,255,255,0.12)',
}

const TRUST_BADGE: Record<string, { icon: string; color: string }> = {
  expert:  { icon: '★', color: 'var(--accent)' },
  normal:  { icon: '·', color: 'var(--muted)' },
  novice:  { icon: '!', color: 'var(--red)' },
  unknown: { icon: '·', color: 'var(--muted)' },
}

const BANK_RISK_COLOR: Record<string, string> = {
  safe:    'var(--green)',
  caution: 'var(--accent)',
  avoid:   'var(--red)',
  unknown: 'var(--muted)',
}

const cellCls = 'px-2 py-1 text-xs'
const headCls = 'px-2 py-1 text-xs font-medium whitespace-nowrap'

export function OrdersTable() {
  const [exchange, setExchange] = useState<Exchange>('binance')
  const [mode, setMode]         = useState<Mode>('buy')
  const [top, setTop]           = useState<Top>(15)
  const [orders, setOrders]     = useState<Order[]>([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  function load(exch: Exchange, md: Mode, tp: Top) {
    setLoading(true)
    setError(null)
    fetchOrders(exch, PAIR, md, tp)
      .then(setOrders)
      .catch(() => setError('Ошибка загрузки'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(exchange, mode, top)
    timerRef.current = setInterval(() => load(exchange, mode, top), REFRESH_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [exchange, mode, top])

  const priceColor = mode === 'buy' ? 'var(--red)' : 'var(--green)'

  return (
    <div className="flex flex-col gap-3">
      {/* Controls */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="font-bold text-sm" style={{ color: 'var(--text)' }}>
          Ордера
        </span>
        <div className="flex gap-2 flex-wrap">
          <select className={selectClass} style={selectStyle} value={exchange}
            onChange={(e) => setExchange(e.target.value as Exchange)}>
            <option value="binance">Binance</option>
            <option value="bybit">Bybit</option>
          </select>

          <select
            className={`${selectClass} min-w-[110px] px-3`}
            style={{ ...selectStyle, fontSize: '0.875rem' }}
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}>
            <option value="buy">Купить</option>
            <option value="sell">Продать</option>
          </select>

          <select className={selectClass} style={selectStyle} value={top}
            onChange={(e) => setTop(Number(e.target.value) as Top)}>
            <option value={10}>10</option>
            <option value={15}>15</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>
      </div>

      {/* States */}
      {loading && (
        <div className="py-8 text-center text-xs" style={{ color: 'var(--muted)' }}>Загрузка…</div>
      )}
      {error && !loading && (
        <div className="py-8 text-center text-xs" style={{ color: 'var(--red)' }}>{error}</div>
      )}
      {!loading && !error && orders.length === 0 && (
        <div className="py-8 text-center text-xs" style={{ color: 'var(--muted)' }}>Нет ордеров</div>
      )}

      {/* Table — без горизонтального скролла */}
      {!loading && !error && orders.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow style={{ borderColor: 'var(--border)' }}>
              {(['Цена', 'Мейкер', 'Объём', 'Лимиты', 'Банки'] as const).map((h) => (
                <TableHead key={h} className={headCls} style={{ color: 'var(--muted)' }}>
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.slice(0, 8).map((order, i) => {
              const badge = TRUST_BADGE[order.maker.trust_level] ?? TRUST_BADGE.unknown
              return (
                <TableRow key={i} style={{ borderColor: 'var(--border)' }}
                  className="hover:bg-white/[0.03] transition-colors">

                  {/* Цена */}
                  <TableCell className={`${cellCls} font-semibold tabular-nums whitespace-nowrap`}
                    style={{ color: priceColor }}>
                    {order.price.toFixed(2)}
                  </TableCell>

                  {/* Мейкер */}
                  <TableCell className={cellCls}>
                    <div className="flex items-center gap-1">
                      <span className="font-bold" style={{ color: badge.color }}>{badge.icon}</span>
                      <span className="truncate max-w-[80px]" style={{ color: 'var(--text)' }}
                        title={order.maker.nickname}>
                        {order.maker.nickname}
                      </span>
                      {order.maker.is_merchant && (
                        <span style={{ color: 'var(--accent)' }} title="Мерчант">⊕</span>
                      )}
                    </div>
                    <div style={{ color: 'var(--muted)' }}>
                      {order.maker.total_orders} сд · {order.maker.completion_rate.toFixed(1)}%
                    </div>
                  </TableCell>

                  {/* Объём */}
                  <TableCell className={`${cellCls} tabular-nums whitespace-nowrap`}
                    style={{ color: 'var(--text)' }}>
                    {order.available_amount.toFixed(0)}
                    <span className="ml-0.5" style={{ color: 'var(--muted)' }}>U</span>
                  </TableCell>

                  {/* Лимиты */}
                  <TableCell className={`${cellCls} whitespace-nowrap`} style={{ color: 'var(--muted)' }}>
                    {Math.round(order.min_amount).toLocaleString('ru-UA')}–{Math.round(order.max_amount).toLocaleString('ru-UA')}
                  </TableCell>

                  {/* Банки — с переносом */}
                  <TableCell className={`${cellCls} whitespace-normal`}>
                    {order.banks.length === 0 ? (
                      <span style={{ color: 'var(--muted)' }}>—</span>
                    ) : (
                      order.banks.map((b, bi) => (
                        <span key={bi}>
                          {bi > 0 && <span style={{ color: 'var(--muted)' }}>, </span>}
                          <span style={{ color: BANK_RISK_COLOR[b.risk] ?? 'var(--muted)' }}>
                            {b.name}
                          </span>
                        </span>
                      ))
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
