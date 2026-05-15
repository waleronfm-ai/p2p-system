import { useEffect, useState } from 'react'
import { fetchTrades, type Trade } from '../lib/api'
import { AddTradeModal } from './AddTradeModal'

// FastAPI returns datetime without 'Z' — append it so JS treats it as UTC
function toUtcDate(iso: string): Date {
  return new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
}

function formatKyiv(iso: string): string {
  const d = toUtcDate(iso)
  const parts = new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Kyiv',
    day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
    hour12: false,
  }).formatToParts(d)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('day')}.${get('month')} ${get('hour')}:${get('minute')}`
}

const cellCls = 'px-2 py-1 text-xs'
const headCls = 'px-2 py-1 text-xs font-medium whitespace-nowrap'

export function TradesHistory() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)

  function load() {
    setLoading(true)
    fetchTrades(50, 0)
      .then(setTrades)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  function handleSaved(trade: Trade) {
    setModalOpen(false)
    setTrades((prev) => [trade, ...prev])
  }

  return (
    <>
      <div className="flex flex-col gap-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="font-bold text-sm" style={{ color: 'var(--text)' }}>
            История
          </span>
          <button
            onClick={() => setModalOpen(true)}
            style={{
              background: 'var(--accent)',
              color: '#000',
              border: 'none',
              borderRadius: 7,
              padding: '4px 12px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            + Добавить
          </button>
        </div>

        {/* Content */}
        {loading && (
          <div className="py-8 text-center text-xs" style={{ color: 'var(--muted)' }}>
            Загрузка…
          </div>
        )}

        {!loading && trades.length === 0 && (
          <div className="py-8 text-center text-xs leading-relaxed" style={{ color: 'var(--muted)' }}>
            Пока нет сделок.<br />Добавьте первую с Binance.
          </div>
        )}

        {!loading && trades.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {(['Дата', 'Тип', 'Курс', 'USDT', 'Банк'] as const).map((h) => (
                    <th key={h} className={headCls} style={{ color: 'var(--muted)', textAlign: 'left' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => {
                  const isBuy = t.trade_type === 'BUY'
                  return (
                    <tr
                      key={t.id}
                      style={{ borderBottom: '1px solid var(--border)' }}
                      className="hover:bg-white/[0.03] transition-colors"
                    >
                      <td className={cellCls} style={{ color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                        {formatKyiv(t.executed_at)}
                      </td>
                      <td className={cellCls} style={{ color: isBuy ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>
                        {t.trade_type}
                      </td>
                      <td className={`${cellCls} tabular-nums`} style={{ color: 'var(--text)' }}>
                        {t.price.toFixed(2)}
                      </td>
                      <td className={`${cellCls} tabular-nums`} style={{ color: 'var(--text)' }}>
                        {t.amount_usdt.toFixed(2)}
                      </td>
                      <td className={cellCls} style={{ color: 'var(--muted)', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {t.bank ?? '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modalOpen && (
        <AddTradeModal
          onSaved={handleSaved}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  )
}
