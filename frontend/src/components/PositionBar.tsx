import { useEffect, useState } from 'react'
import {
  type Position,
  type SessionOut,
  fetchPosition,
  fetchActiveSession,
  startSession,
  closeSession,
} from '../lib/api'

const cardStyle: React.CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: '14px 20px',
}

const dividerStyle: React.CSSProperties = {
  width: 1,
  alignSelf: 'stretch',
  background: 'var(--border)',
  flexShrink: 0,
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5" style={{ minWidth: 0 }}>
      <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{label}</span>
      {children}
    </div>
  )
}

function toUtc(iso: string): Date {
  return new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
}

function formatKyiv(iso: string): string {
  const d = toUtc(iso)
  const parts = new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Kyiv',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(d)
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? ''
  return `${get('day')}.${get('month')} ${get('hour')}:${get('minute')}`
}

function formatDuration(startIso: string, endIso: string): string {
  const diff = toUtc(endIso).getTime() - toUtc(startIso).getTime()
  const h = Math.floor(diff / 3_600_000)
  const m = Math.floor((diff % 3_600_000) / 60_000)
  return h > 0 ? `${h}ч ${m}м` : `${m}м`
}

function pnlColor(v: number): string {
  return v > 0 ? 'var(--green)' : v < 0 ? 'var(--red)' : 'var(--muted)'
}

function fmtUah(v: number | null, decimals = 2): string {
  if (v === null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(decimals)} ₴`
}

// ─── Карточка отчёта при закрытии ───────────────────────────────────────────
function ReportModal({ s, onClose }: { s: SessionOut; onClose: () => void }) {
  const realized = s.realized_uah ?? 0
  const unrealized = s.unrealized_uah ?? 0
  const total = realized + unrealized

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 14,
          padding: 24,
          width: 400,
          maxWidth: '90vw',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>
          Сессия №{s.number} закрыта
        </span>

        <div className="flex flex-col gap-3">
          {/* Стартовый капитал */}
          <div className="flex flex-col gap-0.5">
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>Стартовый капитал</span>
            <span style={{ fontSize: 15, fontWeight: 500, color: 'var(--text)' }}>
              {s.start_capital_uah.toFixed(2)} ₴
            </span>
          </div>

          {/* Реализовано */}
          <div className="flex flex-col gap-0.5">
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>Реализовано</span>
            <span style={{ fontSize: 15, fontWeight: 500, color: pnlColor(realized) }}>
              {fmtUah(s.realized_uah)}
            </span>
            <span style={{ fontSize: 10, color: 'var(--muted)' }}>живые деньги</span>
          </div>

          {/* Нереализовано */}
          <div className="flex flex-col gap-0.5">
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>Нереализовано</span>
            <span style={{ fontSize: 15, fontWeight: 500, color: pnlColor(unrealized) }}>
              {fmtUah(s.unrealized_uah)}
            </span>
            <span style={{ fontSize: 10, color: 'var(--muted)' }}>
              остаток {(s.usdt_remaining ?? 0).toFixed(2)} USDT по курсу{' '}
              {(s.close_sell_price ?? 0).toFixed(2)} ₴, бумажная оценка
            </span>
          </div>

          {/* Итого */}
          <div
            className="flex flex-col gap-0.5"
            style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}
          >
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>ИТОГО (вкл. бумажную часть)</span>
            <span style={{ fontSize: 22, fontWeight: 700, color: pnlColor(total) }}>
              {total >= 0 ? '+' : ''}
              {total.toFixed(2)} ₴
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-1" style={{ fontSize: 12, color: 'var(--muted)' }}>
          {s.closed_at && (
            <span>Длительность: {formatDuration(s.started_at, s.closed_at)}</span>
          )}
          <span>Сделок: {s.trade_count}</span>
        </div>

        <div className="flex justify-end">
          <button
            onClick={onClose}
            style={{
              background: 'var(--accent)',
              color: '#000',
              border: 'none',
              borderRadius: 7,
              padding: '7px 20px',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Диалог подтверждения закрытия ──────────────────────────────────────────
function ConfirmCloseDialog({
  sessionNumber,
  error,
  loading,
  onCancel,
  onConfirm,
}: {
  sessionNumber: number
  error: string | null
  loading: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onCancel()
      }}
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
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
            Закрыть сессию №{sessionNumber}?
          </span>
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>
            Бэкенд возьмёт текущий курс продажи из трекера и зафиксирует P&L.
          </span>
        </div>

        {error && (
          <div
            style={{
              background: 'rgba(239,68,68,0.1)',
              color: 'var(--red)',
              borderRadius: 6,
              padding: '8px 10px',
              fontSize: 12,
            }}
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
            {loading ? 'Закрытие…' : 'Закрыть сессию'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Блок сессии: форма старта или шапка активной ───────────────────────────
function SessionSection({
  session,
  sessionLoaded,
  onStart,
  onCloseClick,
}: {
  session: SessionOut | null
  sessionLoaded: boolean
  onStart: (capital: number, exchange: string) => Promise<void>
  onCloseClick: () => void
}) {
  const [capital, setCapital] = useState('')
  const [exchange, setExchange] = useState('binance')
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  const capNum = parseFloat(capital)
  const canStart = !isNaN(capNum) && capNum > 0 && !starting

  async function handleStart() {
    if (!canStart) return
    setStarting(true)
    setStartError(null)
    try {
      await onStart(capNum, exchange)
      setCapital('')
    } catch {
      setStartError('Ошибка при старте сессии. Попробуйте ещё раз.')
    } finally {
      setStarting(false)
    }
  }

  if (!sessionLoaded) {
    return (
      <Block label="Сессия">
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>…</span>
      </Block>
    )
  }

  if (session === null) {
    return (
      <Block label="Новая сессия">
        <div className="flex items-center gap-1.5">
          <input
            type="number"
            min={1}
            placeholder="Капитал ₴"
            value={capital}
            onChange={(e) => setCapital(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleStart() }}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--text)',
              padding: '4px 8px',
              fontSize: 13,
              width: 95,
              outline: 'none',
            }}
          />
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--text)',
              padding: '4px 6px',
              fontSize: 13,
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="binance">Binance</option>
            <option value="bybit">Bybit</option>
          </select>
          <button
            onClick={handleStart}
            disabled={!canStart}
            style={{
              background: canStart ? 'var(--accent)' : 'rgba(255,255,255,0.08)',
              color: canStart ? '#000' : 'var(--muted)',
              border: 'none',
              borderRadius: 7,
              padding: '5px 12px',
              fontSize: 12,
              fontWeight: 600,
              cursor: canStart ? 'pointer' : 'default',
              whiteSpace: 'nowrap',
            }}
          >
            {starting ? 'Старт…' : 'Старт'}
          </button>
        </div>
        {startError && (
          <span style={{ fontSize: 10, color: 'var(--red)' }}>{startError}</span>
        )}
      </Block>
    )
  }

  return (
    <Block label={`Сессия №${session.number}`}>
      <div className="flex items-center gap-2">
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--green)', whiteSpace: 'nowrap' }}>
          активна
        </span>
        <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
          {session.start_capital_uah.toFixed(0)} ₴ · {formatKyiv(session.started_at)} · {session.exchange}
        </span>
        <button
          onClick={onCloseClick}
          style={{
            background: 'transparent',
            border: '1px solid var(--border)',
            borderRadius: 7,
            color: 'var(--muted)',
            padding: '3px 10px',
            fontSize: 11,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--red)'
            e.currentTarget.style.color = 'var(--red)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border)'
            e.currentTarget.style.color = 'var(--muted)'
          }}
        >
          Закрыть
        </button>
      </div>
    </Block>
  )
}

// ─── Главный компонент ───────────────────────────────────────────────────────
export function PositionBar() {
  const [pos, setPos] = useState<Position | null>(null)
  const [posReady, setPosReady] = useState(false)
  const [session, setSession] = useState<SessionOut | null>(null)
  const [sessionLoaded, setSessionLoaded] = useState(false)
  const [confirmClose, setConfirmClose] = useState(false)
  const [closing, setClosing] = useState(false)
  const [closeError, setCloseError] = useState<string | null>(null)
  const [report, setReport] = useState<SessionOut | null>(null)

  useEffect(() => {
    const loadPos = () =>
      fetchPosition()
        .then((p) => {
          setPos(p)
          setPosReady(true)
        })
        .catch(() => setPosReady(true))
    loadPos()
    const id = setInterval(loadPos, 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    fetchActiveSession()
      .then(setSession)
      .catch(() => {})
      .finally(() => setSessionLoaded(true))
  }, [])

  async function handleStart(capital: number, exchange: string) {
    const s = await startSession(capital, exchange)
    setSession(s)
  }

  async function handleConfirmClose() {
    if (!session) return
    setClosing(true)
    setCloseError(null)
    try {
      const closed = await closeSession(session.id)
      setSession(null)
      setConfirmClose(false)
      setReport(closed)
    } catch (err) {
      setCloseError(err instanceof Error ? err.message : 'Ошибка при закрытии сессии. Попробуйте ещё раз.')
    } finally {
      setClosing(false)
    }
  }

  if (!posReady) {
    return (
      <div style={cardStyle}>
        <span style={{ fontSize: 13, color: 'var(--muted)' }}>Загрузка позиции…</span>
      </div>
    )
  }

  const balance = pos?.usdt_balance ?? 0
  const avgBuy = pos?.avg_buy_price ?? null
  const profit = pos?.realized_profit_uah ?? null
  const total = pos?.total_trades ?? 0
  const buyCnt = pos?.buy_count ?? 0
  const sellCnt = pos?.sell_count ?? 0

  const profitColor =
    profit === null || profit === 0
      ? 'var(--muted)'
      : profit > 0
        ? 'var(--green)'
        : 'var(--red)'

  const profitText =
    profit === null || profit === 0
      ? '0 ₴'
      : `${profit > 0 ? '+' : ''}${profit.toFixed(2)} ₴`

  return (
    <>
      <div style={cardStyle}>
        <div className="flex items-center gap-5" style={{ flexWrap: 'wrap' }}>

          <SessionSection
            session={session}
            sessionLoaded={sessionLoaded}
            onStart={handleStart}
            onCloseClick={() => {
              setConfirmClose(true)
              setCloseError(null)
            }}
          />

          <div style={dividerStyle} />

          <Block label="На руках">
            <span
              style={{
                fontSize: 20,
                fontWeight: 600,
                color: balance > 0 ? 'var(--text)' : 'var(--muted)',
                whiteSpace: 'nowrap',
              }}
            >
              {balance.toFixed(2)}{' '}
              <span style={{ fontSize: 14, fontWeight: 400 }}>USDT</span>
            </span>
          </Block>

          <div style={dividerStyle} />

          <Block label="Средний курс покупки">
            <span
              style={{
                fontSize: 18,
                fontWeight: 500,
                color: avgBuy !== null ? 'var(--text)' : 'var(--muted)',
                whiteSpace: 'nowrap',
              }}
            >
              {avgBuy !== null ? `${avgBuy.toFixed(2)} ₴` : '—'}
            </span>
          </Block>

          <div style={dividerStyle} />

          <Block label="Реализованная прибыль">
            <span
              style={{
                fontSize: 18,
                fontWeight: 500,
                color: profitColor,
                whiteSpace: 'nowrap',
              }}
            >
              {profitText}
            </span>
          </Block>

          <div style={dividerStyle} />

          <Block label="Сделок">
            <span style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)' }}>{total}</span>
            <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
              BUY {buyCnt} · SELL {sellCnt}
            </span>
          </Block>

        </div>
      </div>

      {confirmClose && session && (
        <ConfirmCloseDialog
          sessionNumber={session.number}
          error={closeError}
          loading={closing}
          onCancel={() => {
            if (!closing) {
              setConfirmClose(false)
              setCloseError(null)
            }
          }}
          onConfirm={handleConfirmClose}
        />
      )}

      {report && <ReportModal s={report} onClose={() => setReport(null)} />}
    </>
  )
}
