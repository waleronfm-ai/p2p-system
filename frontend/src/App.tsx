import { useEffect, useState } from 'react'
import { OrdersTable } from './components/OrdersTable'
import { PriceChart } from './components/PriceChart'
import { fetchHealth } from './lib/api'

const cardStyle: React.CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 20,
}

const placeholderTitles = ['AI-агент', 'История']

function PlaceholderCard({ title }: { title: string }) {
  return (
    <div style={{ ...cardStyle, minHeight: 120 }} className="flex items-center justify-center">
      <span className="text-sm" style={{ color: 'var(--muted)' }}>
        {title}
      </span>
    </div>
  )
}

export default function App() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    fetchHealth().then(setApiOnline)
    const id = setInterval(() => fetchHealth().then(setApiOnline), 30_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex flex-col px-6 py-4" style={{ background: 'var(--background)' }}>
      {/* Header */}
      <header
        className="flex items-center justify-between pb-3 mb-4 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        <span className="text-lg font-bold tracking-wide" style={{ color: 'var(--accent)' }}>
          P2P Coach
        </span>

        <div className="flex items-center gap-2 text-sm">
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{
              background:
                apiOnline === null ? 'var(--muted)' : apiOnline ? 'var(--green)' : 'var(--red)',
            }}
          />
          <span style={{ color: apiOnline ? 'var(--green)' : apiOnline === false ? 'var(--red)' : 'var(--muted)' }}>
            {apiOnline === null ? 'Проверка…' : apiOnline ? 'API онлайн' : 'API офлайн'}
          </span>
        </div>
      </header>

      {/* Main grid — ячейки не растягиваются, каждая по своему содержимому */}
      <main>
        <div
          className="dashboard-grid grid gap-4 items-start auto-rows-min"
          style={{ gridTemplateColumns: 'repeat(2, 1fr)', gridAutoRows: 'min-content' }}
        >
          {/* Chart — top-left */}
          <div style={cardStyle}>
            <PriceChart />
          </div>

          {/* Orders — top-right */}
          <div style={cardStyle}>
            <OrdersTable />
          </div>

          {placeholderTitles.map((title) => (
            <PlaceholderCard key={title} title={title} />
          ))}
        </div>
      </main>
    </div>
  )
}
