import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Header } from './components/Header'
import { Dashboard } from './pages/Dashboard'
import { Statistics } from './pages/Statistics'
import { Faq } from './pages/Faq'

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
          <Route path="/faq" element={<Faq />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
