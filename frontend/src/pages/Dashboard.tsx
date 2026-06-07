import { AIAgentCard } from '../components/AIAgentCard'
import { PositionBar } from '../components/PositionBar'
import { PriceChart } from '../components/PriceChart'
import { SessionsSummary } from '../components/SessionsSummary'
import { TrackerHealthWidget } from '../components/TrackerHealthWidget'
import { TradesHistory } from '../components/TradesHistory'

const cardStyle: React.CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 20,
}

export function Dashboard() {
  return (
    <main className="flex flex-col gap-4">
      <TrackerHealthWidget />
      <PositionBar />

      <div style={cardStyle}>
        <PriceChart />
      </div>

      <AIAgentCard />

      <div style={cardStyle}>
        <SessionsSummary />
      </div>

      <div style={cardStyle}>
        <TradesHistory />
      </div>
    </main>
  )
}
