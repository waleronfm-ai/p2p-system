import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Header } from './components/Header'
import { Dashboard } from './pages/Dashboard'
import { Statistics } from './pages/Statistics'

export default function App() {
  return (
    <BrowserRouter>
      <div
        className="flex flex-col min-h-screen px-6 py-4"
        style={{ background: 'var(--background)' }}
      >
        <Header />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/stats" element={<Statistics />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
