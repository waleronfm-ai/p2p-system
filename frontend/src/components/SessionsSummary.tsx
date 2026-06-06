import { useEffect, useState } from 'react'
import { fetchSessions, type SessionOut } from '../lib/api'

export function SessionsSummary() {
  const [sessions, setSessions] = useState<SessionOut[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSessions()
      .then(setSessions)
      .finally(() => setLoading(false))
  }, [])

  const closed = sessions.filter((s) => s.status === 'closed')
  const totalRealized = closed.reduce((sum, s) => sum + (s.realized_uah ?? 0), 0)
  const hasUnrealized = closed.some((s) => s.unrealized_uah != null)
  const totalUnrealized = closed.reduce((sum, s) => sum + (s.unrealized_uah ?? 0), 0)

  return (
    <div className="flex flex-col gap-3">
      <span className="font-bold text-sm" style={{ color: 'var(--text)' }}>
        Общий учёт по сессиям
      </span>

      {loading && (
        <div className="text-xs" style={{ color: 'var(--muted)' }}>Загрузка…</div>
      )}

      {!loading && closed.length === 0 && (
        <div className="text-xs" style={{ color: 'var(--muted)' }}>
          Пока нет закрытых сессий
        </div>
      )}

      {!loading && closed.length > 0 && (
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs" style={{ color: 'var(--muted)' }}>Закрыто сессий</span>
            <span className="text-sm font-semibold tabular-nums" style={{ color: 'var(--text)' }}>
              {closed.length}
            </span>
          </div>

          <div className="flex flex-col gap-0.5">
            <span className="text-xs" style={{ color: 'var(--muted)' }}>
              Реализовано <span style={{ opacity: 0.6 }}>живые деньги</span>
            </span>
            <span
              className="text-sm font-semibold tabular-nums"
              style={{ color: totalRealized >= 0 ? 'var(--green)' : 'var(--red)' }}
            >
              {totalRealized >= 0 ? '+' : ''}{totalRealized.toFixed(2)} ₴
            </span>
          </div>

          {hasUnrealized && (
            <div className="flex flex-col gap-0.5">
              <span className="text-xs" style={{ color: 'var(--muted)' }}>Нереализовано</span>
              <span
                className="text-sm font-semibold tabular-nums"
                style={{ color: totalUnrealized >= 0 ? 'var(--green)' : 'var(--red)' }}
              >
                {totalUnrealized >= 0 ? '+' : ''}{totalUnrealized.toFixed(2)} ₴
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
