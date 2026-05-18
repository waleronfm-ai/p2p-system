import { PriceChart } from '../components/PriceChart'
import { TradesHistory } from '../components/TradesHistory'

const cardStyle: React.CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 20,
}

function AIAgentCard() {
  return (
    <div
      style={{ ...cardStyle, minHeight: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
    >
      <span className="text-sm" style={{ color: 'var(--muted)' }}>
        AI-агент скоро появится
      </span>
    </div>
  )
}

export function Dashboard() {
  return (
    <main className="flex flex-col gap-4">
      <div style={cardStyle}>
        <PriceChart />
      </div>

      <AIAgentCard />

      <div style={cardStyle}>
        <TradesHistory />
      </div>
    </main>
  )
}
