import { useEffect, useState } from 'react'
import { type Position, fetchPosition } from '../lib/api'

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

export function PositionBar() {
  const [pos, setPos] = useState<Position | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const load = () =>
      fetchPosition()
        .then((p) => {
          setPos(p)
          setReady(true)
        })
        .catch(() => setReady(true))

    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  if (!ready) {
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
    <div style={cardStyle}>
      <div className="flex items-center gap-5" style={{ flexWrap: 'wrap' }}>

        {/* Блок 1: На руках */}
        <Block label="На руках">
          <span
            style={{
              fontSize: 20,
              fontWeight: 600,
              color: balance > 0 ? 'var(--text)' : 'var(--muted)',
              whiteSpace: 'nowrap',
            }}
          >
            {balance.toFixed(2)} <span style={{ fontSize: 14, fontWeight: 400 }}>USDT</span>
          </span>
        </Block>

        <div style={dividerStyle} />

        {/* Блок 2: Средний курс покупки */}
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

        {/* Блок 3: Реализованная прибыль */}
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

        {/* Блок 4: Сделок */}
        <Block label="Сделок">
          <span style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)' }}>
            {total}
          </span>
          <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
            BUY {buyCnt} · SELL {sellCnt}
          </span>
        </Block>

      </div>
    </div>
  )
}
