import { useState } from 'react'
import { analyzeAI } from '../lib/api'

type Mode = 'sessions' | 'market'

const MODE_LABELS: Record<Mode, string> = {
  sessions: 'Разбор сессий',
  market: 'Рынок',
}

const MODE_HINTS: Record<Mode, string> = {
  sessions: 'последние закрытые сессии',
  market: '30 дней истории',
}

export function AIAgentCard() {
  const [loading, setLoading] = useState(false)
  const [activeMode, setActiveMode] = useState<Mode | null>(null)
  const [result, setResult] = useState<{ mode: Mode; text: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleAnalyze(mode: Mode) {
    if (loading) return
    setLoading(true)
    setActiveMode(mode)
    setError(null)
    try {
      const text = await analyzeAI(mode)
      setResult({ mode, text })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Неизвестная ошибка. Попробуй ещё раз.')
      setResult(null)
    } finally {
      setLoading(false)
      setActiveMode(null)
    }
  }

  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 20,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      {/* Заголовок */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>AI-аналитик</span>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>факты и наблюдения, решение за тобой</span>
      </div>

      {/* Кнопки */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {(['sessions', 'market'] as Mode[]).map((mode) => {
          const isThisActive = activeMode === mode
          const isDisabled = loading

          return (
            <button
              key={mode}
              onClick={() => handleAnalyze(mode)}
              disabled={isDisabled}
              style={{
                background: isThisActive
                  ? 'rgba(255,255,255,0.11)'
                  : 'rgba(255,255,255,0.06)',
                color: isDisabled ? 'var(--muted)' : 'var(--text)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: '7px 18px',
                fontSize: 13,
                fontWeight: 500,
                cursor: isDisabled ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'background 0.12s',
              }}
              onMouseEnter={(e) => {
                if (!isDisabled)
                  e.currentTarget.style.background = 'rgba(255,255,255,0.13)'
              }}
              onMouseLeave={(e) => {
                if (!isDisabled)
                  e.currentTarget.style.background = isThisActive
                    ? 'rgba(255,255,255,0.11)'
                    : 'rgba(255,255,255,0.06)'
              }}
            >
              {isThisActive && (
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    border: '2px solid var(--muted)',
                    borderTopColor: 'transparent',
                    display: 'inline-block',
                    animation: 'spin 0.7s linear infinite',
                    flexShrink: 0,
                  }}
                />
              )}
              {isThisActive ? 'Анализирую…' : MODE_LABELS[mode]}
              {!isThisActive && (
                <span style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 400 }}>
                  {MODE_HINTS[mode]}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Ошибка */}
      {error && (
        <div
          style={{
            background: 'rgba(239,68,68,0.1)',
            color: 'var(--red)',
            borderRadius: 7,
            padding: '10px 12px',
            fontSize: 12,
            lineHeight: 1.5,
          }}
        >
          {error}
        </div>
      )}

      {/* Результат */}
      {result && !error && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {MODE_LABELS[result.mode]}
          </span>
          <div
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '12px 14px',
              fontSize: 13,
              lineHeight: 1.65,
              color: 'var(--text)',
              whiteSpace: 'pre-wrap',
            }}
          >
            {result.text}
          </div>
        </div>
      )}

      {/* Анимация спиннера */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
