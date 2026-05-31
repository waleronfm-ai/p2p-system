import { useEffect, useRef, useState } from 'react'
import { fetchTrackerHealth, type TrackerHealth } from '../lib/api'

type StatusKey = 'alive' | 'slow' | 'dead' | 'no_api'

function resolveStatus(data: TrackerHealth | null, errCount: number): StatusKey {
  if (errCount >= 2) return 'no_api'
  if (!data || !data.tracker_alive || data.minutes_since_last_snapshot === null) return 'dead'
  const m = data.minutes_since_last_snapshot
  if (m < 5) return 'alive'
  if (m < 15) return 'slow'
  return 'dead'
}

const STATUS_COLOR: Record<StatusKey, string> = {
  alive: '#22C55E',
  slow: '#F7A600',
  dead: '#EF4444',
  no_api: '#EF4444',
}

function statusLabel(key: StatusKey, minutes: number | null): string {
  if (key === 'alive') return 'Трекер активен'
  if (key === 'slow') return `Молчит ${Math.round(minutes ?? 0)} мин`
  if (key === 'dead') return 'Не отвечает'
  return 'Нет связи с API'
}

function lastSeenText(minutes: number | null): string {
  if (minutes === null) return '—'
  if (minutes < 1) return 'только что'
  return `${Math.round(minutes)} мин назад`
}

function fmt(n: number): string {
  return n.toLocaleString('ru-RU')
}

const divider = (
  <div style={{ width: 1, alignSelf: 'stretch', background: 'var(--border)', flexShrink: 0 }} />
)

export function TrackerHealthWidget() {
  const [data, setData] = useState<TrackerHealth | null>(null)
  const [errCount, setErrCount] = useState(0)
  const errRef = useRef(0)

  const load = async () => {
    try {
      const result = await fetchTrackerHealth()
      setData(result)
      errRef.current = 0
      setErrCount(0)
    } catch {
      errRef.current += 1
      setErrCount(errRef.current)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  const status = resolveStatus(data, errCount)
  const color = STATUS_COLOR[status]
  const label = statusLabel(status, data?.minutes_since_last_snapshot ?? null)

  return (
    <div style={{
      background: '#1A1E1E',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '8px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: 20,
      flexWrap: 'wrap',
    }}>

      {/* Статус */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, padding: '4px 0' }}>
        <div style={{
          width: 9,
          height: 9,
          borderRadius: '50%',
          background: color,
          boxShadow: `0 0 5px ${color}`,
          flexShrink: 0,
        }} />
        <span style={{ color, fontSize: 13, fontWeight: 600 }}>{label}</span>
        {data && status !== 'no_api' && (
          <span style={{ color: '#6B6B7A', fontSize: 12 }}>
            · Снапшот: {lastSeenText(data.minutes_since_last_snapshot)}
          </span>
        )}
      </div>

      {divider}

      {/* За последний час */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1, padding: '4px 0' }}>
        <span style={{ color: '#6B6B7A', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          За последний час
        </span>
        <div style={{ display: 'flex', gap: 14 }}>
          <span style={{ color: '#E8E8EC', fontSize: 12 }}>
            Снапшоты:&nbsp;<b>{fmt(data?.snapshots_last_hour ?? 0)}</b>
          </span>
          <span style={{ color: '#E8E8EC', fontSize: 12 }}>
            Ордера:&nbsp;<b>{fmt(data?.orders_last_hour ?? 0)}</b>
          </span>
        </div>
      </div>

      {divider}

      {/* Всего в БД */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1, padding: '4px 0' }}>
        <span style={{ color: '#6B6B7A', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Всего в БД
        </span>
        <div style={{ display: 'flex', gap: 14 }}>
          <span style={{ color: '#E8E8EC', fontSize: 12 }}>
            Снапшоты:&nbsp;<b>{fmt(data?.total_snapshots ?? 0)}</b>
          </span>
          <span style={{ color: '#E8E8EC', fontSize: 12 }}>
            Ордера:&nbsp;<b>{fmt(data?.total_orders ?? 0)}</b>
          </span>
        </div>
      </div>

      {divider}

      {/* Размер БД */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1, padding: '4px 0' }}>
        <span style={{ color: '#6B6B7A', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Размер БД
        </span>
        <span style={{ color: '#E8E8EC', fontSize: 12 }}>
          <b>{data != null ? `${data.db_size_mb.toFixed(1)} МБ` : '—'}</b>
        </span>
      </div>

    </div>
  )
}
