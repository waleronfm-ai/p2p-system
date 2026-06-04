import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { fetchHealth } from '../lib/api'

export function Header() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    fetchHealth().then(setApiOnline)
    const id = setInterval(() => fetchHealth().then(setApiOnline), 30_000)
    return () => clearInterval(id)
  }, [])

  return (
    <header
      className="flex items-center justify-between pb-3 mb-4 border-b"
      style={{ borderColor: 'var(--border)' }}
    >
      <div className="flex items-center gap-6">
        <span className="text-lg font-bold tracking-wide" style={{ color: 'var(--accent)' }}>
          P2P Coach
        </span>
        <nav className="flex items-center gap-4 text-sm">
          <NavLink
            to="/"
            end
            style={({ isActive }) => ({ color: isActive ? 'var(--accent)' : 'var(--muted)', textDecoration: 'none', fontWeight: 500 })}
          >
            Дашборд
          </NavLink>
          <NavLink
            to="/stats"
            style={({ isActive }) => ({ color: isActive ? 'var(--accent)' : 'var(--muted)', textDecoration: 'none', fontWeight: 500 })}
          >
            Статистика
          </NavLink>
          <NavLink
            to="/faq"
            style={({ isActive }) => ({ color: isActive ? 'var(--accent)' : 'var(--muted)', textDecoration: 'none', fontWeight: 500 })}
          >
            FAQ
          </NavLink>
        </nav>
      </div>

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
  )
}
