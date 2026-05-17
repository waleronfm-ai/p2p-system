import { OrdersTable } from '../components/OrdersTable'
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
    <div style={{ ...cardStyle, minHeight: 120 }} className="flex items-center justify-center">
      <span className="text-sm" style={{ color: 'var(--muted)' }}>
        AI-агент
      </span>
    </div>
  )
}

export function Dashboard() {
  return (
    <main>
      <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
        {/* Левая колонка: График + AI-агент */}
        <div className="flex flex-col gap-4">
          <div style={cardStyle}>
            <PriceChart />
          </div>
          <AIAgentCard />
        </div>

        {/* Правая колонка: Ордера + История */}
        <div className="flex flex-col gap-4">
          <div style={cardStyle}>
            <OrdersTable />
          </div>
          <div style={cardStyle}>
            <TradesHistory />
          </div>
        </div>
      </div>
    </main>
  )
}
