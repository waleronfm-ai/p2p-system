import { useEffect, useState } from 'react'
import { fetchTrades, deleteTrade, type Trade } from '../lib/api'
import { AddTradeModal } from './AddTradeModal'
import { Trash2 } from 'lucide-react'

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

interface ConfirmDeleteDialogProps {
  onCancel: () => void
  onConfirm: () => void
  loading: boolean
  error: string | null
}

function ConfirmDeleteDialog({ onCancel, onConfirm, loading, error }: ConfirmDeleteDialogProps) {
  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 200,
      }}
      onClick={(e) => { if (e.target === e.currentTarget && !loading) onCancel() }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 14,
          padding: 24,
          width: 360,
          maxWidth: '90vw',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <div className="flex flex-col gap-1">
          <span className="font-bold text-sm" style={{ color: 'var(--text)' }}>
            Удалить сделку?
          </span>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            Это действие необратимо. Сделка будет удалена навсегда.
          </span>
        </div>

        {error && (
          <div
            className="text-xs rounded p-2"
            style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}
          >
            {error}
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            disabled={loading}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: 8,
              color: 'var(--muted)',
              padding: '7px 16px',
              fontSize: 13,
              cursor: loading ? 'default' : 'pointer',
              opacity: loading ? 0.5 : 1,
            }}
          >
            Отмена
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            style={{
              background: loading ? 'rgba(239,68,68,0.5)' : 'rgb(239,68,68)',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              padding: '7px 16px',
              fontSize: 13,
              fontWeight: 600,
              cursor: loading ? 'default' : 'pointer',
            }}
          >
            {loading ? 'Удаление…' : 'Удалить'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function TradesHistory() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

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

  function openDeleteDialog(id: number) {
    setDeleteTarget(id)
    setDeleteError(null)
  }

  function closeDeleteDialog() {
    if (deleting) return
    setDeleteTarget(null)
    setDeleteError(null)
  }

  async function handleConfirmDelete() {
    if (deleteTarget === null) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await deleteTrade(deleteTarget)
      setTrades((prev) => prev.filter((t) => t.id !== deleteTarget))
      setDeleteTarget(null)
    } catch {
      setDeleteError('Не удалось удалить сделку. Попробуйте ещё раз.')
    } finally {
      setDeleting(false)
    }
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
                  {['Дата', 'Тип', 'Курс', 'USDT', 'Банк', ''].map((h, i) => (
                    <th key={i} className={headCls} style={{ color: 'var(--muted)', textAlign: 'left' }}>
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
                      <td className={cellCls} style={{ width: 28, textAlign: 'right' }}>
                        <button
                          onClick={() => openDeleteDialog(t.id)}
                          title="Удалить сделку"
                          style={{
                            background: 'none',
                            border: 'none',
                            padding: 2,
                            cursor: 'pointer',
                            color: 'var(--muted)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            borderRadius: 4,
                            transition: 'color 0.15s',
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--red)' }}
                          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--muted)' }}
                        >
                          <Trash2 size={13} />
                        </button>
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

      {deleteTarget !== null && (
        <ConfirmDeleteDialog
          onCancel={closeDeleteDialog}
          onConfirm={handleConfirmDelete}
          loading={deleting}
          error={deleteError}
        />
      )}
    </>
  )
}
