import { useEffect, useState } from 'react'
import type { TradeStats } from '../lib/api'
import { fetchTradeStats } from '../lib/api'

const cardStyle: React.CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 20,
}

type Period = '7d' | '30d' | 'all'

const PERIOD_LABELS: Record<Period, string> = {
  '7d': '7 дней',
  '30d': '30 дней',
  'all': 'Всё время',
}

function getFromDt(period: Period): string | undefined {
  if (period === 'all') return undefined
  const days = period === '7d' ? 7 : 30
  const d = new Date()
  d.setUTCDate(d.getUTCDate() - days)
  d.setUTCHours(0, 0, 0, 0)
  return d.toISOString()
}

function fmtUah(val: number): string {
  const sign = val > 0 ? '+' : val < 0 ? '' : ''
  return `${sign}${val.toLocaleString('ru-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₴`
}

function fmtNum(val: number, decimals = 2): string {
  return val.toLocaleString('ru-UA', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function MetricCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={cardStyle}>
      <div className="text-xs mb-3" style={{ color: 'var(--muted)' }}>{title}</div>
      {children}
    </div>
  )
}

export function Statistics() {
  const [period, setPeriod] = useState<Period>('30d')
  const [stats, setStats] = useState<TradeStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchTradeStats(getFromDt(period))
      .then(setStats)
      .finally(() => setLoading(false))
  }, [period])

  return (
    <main className="flex flex-col gap-4">
      {/* Заголовок + выбор периода */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold" style={{ color: 'var(--text)' }}>Статистика</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
            {PERIOD_LABELS[period]}
          </p>
        </div>
        <div className="flex gap-2">
          {(['7d', '30d', 'all'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className="px-3 py-1 rounded text-sm font-medium transition-colors"
              style={{
                background: period === p ? 'var(--accent)' : 'var(--surface)',
                color: period === p ? '#0E0E10' : 'var(--muted)',
                border: '1px solid var(--border)',
                cursor: 'pointer',
              }}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <p className="text-sm" style={{ color: 'var(--muted)' }}>Загрузка…</p>
      )}

      {!loading && stats && stats.total_trades === 0 && (
        <div
          className="flex items-center justify-center"
          style={{ ...cardStyle, minHeight: 200 }}
        >
          <p className="text-sm text-center" style={{ color: 'var(--muted)' }}>
            Нет сделок за выбранный период.<br />
            Добавьте сделки в блоке История.
          </p>
        </div>
      )}

      {!loading && stats && stats.total_trades > 0 && (
        <>
          {/* Большая карточка прибыли */}
          <div style={{ ...cardStyle, padding: 32 }}>
            <div className="text-sm mb-2" style={{ color: 'var(--muted)' }}>Прибыль</div>
            <div
              className="text-4xl font-bold"
              style={{
                color: stats.pnl_uah > 0
                  ? 'var(--green)'
                  : stats.pnl_uah < 0
                    ? 'var(--red)'
                    : 'var(--muted)',
              }}
            >
              {fmtUah(stats.pnl_uah)}
            </div>
          </div>

          {/* Сетка метрик */}
          <div
            className="grid gap-4"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}
          >
            {/* Сделок всего */}
            <MetricCard title="Сделок всего">
              <div className="text-2xl font-bold" style={{ color: 'var(--text)' }}>
                {stats.total_trades}
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
                куплено: {stats.buy_count}, продано: {stats.sell_count}
              </div>
            </MetricCard>

            {/* Объём */}
            <MetricCard title="Объём">
              <div className="text-sm" style={{ color: 'var(--green)' }}>
                куплено: {fmtNum(stats.total_usdt_bought)} USDT
              </div>
              <div className="text-sm mt-1" style={{ color: 'var(--red)' }}>
                продано: {fmtNum(stats.total_usdt_sold)} USDT
              </div>
            </MetricCard>

            {/* Средние курсы */}
            <MetricCard title="Средние курсы">
              <div className="text-sm" style={{ color: 'var(--green)' }}>
                Покупка: {stats.avg_buy_price != null ? `${fmtNum(stats.avg_buy_price)} ₴` : '—'}
              </div>
              <div className="text-sm mt-1" style={{ color: 'var(--red)' }}>
                Продажа: {stats.avg_sell_price != null ? `${fmtNum(stats.avg_sell_price)} ₴` : '—'}
              </div>
              {stats.avg_buy_price != null && stats.avg_sell_price != null && (
                <div className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
                  Разница: {fmtNum(stats.avg_sell_price - stats.avg_buy_price)} ₴
                </div>
              )}
            </MetricCard>

            {/* Обороты */}
            <MetricCard title="Обороты">
              <div className="text-sm" style={{ color: 'var(--muted)' }}>
                Потрачено: {fmtNum(stats.total_uah_spent)} ₴
              </div>
              <div className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
                Получено: {fmtNum(stats.total_uah_received)} ₴
              </div>
            </MetricCard>
          </div>
        </>
      )}
    </main>
  )
}
