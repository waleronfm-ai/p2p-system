import { OrdersTable } from '../components/OrdersTable'
import { PriceChart } from '../components/PriceChart'
import { TradesHistory } from '../components/TradesHistory'

const cardStyle: React.CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 20,
}

const placeholderTitles = ['AI-агент']

function PlaceholderCard({ title }: { title: string }) {
  return (
    <div style={{ ...cardStyle, minHeight: 120 }} className="flex items-center justify-center">
      <span className="text-sm" style={{ color: 'var(--muted)' }}>
        {title}
      </span>
    </div>
  )
}

export function Dashboard() {
  return (
    <main>
      <div
        className="dashboard-grid grid gap-4 items-start auto-rows-min"
        style={{ gridTemplateColumns: 'repeat(2, 1fr)', gridAutoRows: 'min-content' }}
      >
        <div style={cardStyle}>
          <PriceChart />
        </div>

        <div style={cardStyle}>
          <OrdersTable />
        </div>

        <div style={cardStyle}>
          <TradesHistory />
        </div>

        {placeholderTitles.map((title) => (
          <PlaceholderCard key={title} title={title} />
        ))}
      </div>
    </main>
  )
}
