import { useRef, useState } from 'react'
import { createTrade, type Trade } from '../lib/api'
import { parseBinanceTrade, type ParsedTrade } from '../lib/binanceParser'

const PLACEHOLDER = `Номер ордера
22865064847464288256
ПродатьUSDT
Сумма в фиате
₴ 3,784.44
Цена
₴ 43.66
Общее кол-во
86.75 USDT
Время создания
2026-03-11 18:05:36
Способ оплаты
Monobank (Card)`

const overlayStyle: React.CSSProperties = {
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.6)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 100,
}

const modalStyle: React.CSSProperties = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 14,
  padding: 24,
  width: 440,
  maxWidth: '95vw',
  maxHeight: '90vh',
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
}

const inputStyle: React.CSSProperties = {
  background: 'var(--background)',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 8,
  color: 'var(--text)',
  padding: '6px 10px',
  fontSize: 13,
  width: '100%',
  boxSizing: 'border-box',
}

interface Props {
  onSaved: (trade: Trade) => void
  onClose: () => void
}

interface ParseError { message: string }

export function AddTradeModal({ onSaved, onClose }: Props) {
  const [raw, setRaw] = useState('')
  const [parsed, setParsed] = useState<ParsedTrade | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [counterparty, setCounterparty] = useState('')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleParse() {
    setParseError(null)
    setParsed(null)
    setSaveError(null)
    const result = parseBinanceTrade(raw)
    if (!result) {
      setParseError('Не удалось распарсить текст. Проверьте что скопировали всю страницу сделки.')
      return
    }
    setParsed(result)
  }

  async function handleSave() {
    if (!parsed) return
    setSaving(true)
    setSaveError(null)
    try {
      const trade = await createTrade({
        ...parsed,
        counterparty: counterparty.trim() || null,
        note: note.trim() || null,
      })
      onSaved(trade)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 409) {
        setSaveError('Эта сделка уже добавлена (дубликат order_id).')
      } else {
        setSaveError('Ошибка сохранения. Попробуйте ещё раз.')
      }
    } finally {
      setSaving(false)
    }
  }

  const isBuy = parsed?.trade_type === 'BUY'
  const typeColor = isBuy ? 'var(--green)' : 'var(--red)'

  function formatDate(iso: string) {
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
    return d.toLocaleString('ru-RU', {
      timeZone: 'Europe/Kyiv',
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
      hour12: false,
    })
  }

  return (
    <div style={overlayStyle} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={modalStyle}>
        <div className="flex items-center justify-between">
          <span className="font-bold text-sm" style={{ color: 'var(--text)' }}>
            Добавить сделку
          </span>
          <button onClick={onClose} style={{ color: 'var(--muted)', fontSize: 18, lineHeight: 1 }}>×</button>
        </div>

        {/* Textarea */}
        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: 'var(--muted)' }}>
            Вставьте текст со страницы сделки Binance
          </label>
          <textarea
            ref={textareaRef}
            value={raw}
            onChange={(e) => { setRaw(e.target.value); setParsed(null); setParseError(null) }}
            placeholder={PLACEHOLDER}
            rows={8}
            style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
          />
        </div>

        <button
          onClick={handleParse}
          disabled={!raw.trim()}
          style={{
            background: raw.trim() ? 'var(--accent)' : 'var(--border)',
            color: raw.trim() ? '#000' : 'var(--muted)',
            border: 'none', borderRadius: 8,
            padding: '8px 16px', fontSize: 13, fontWeight: 600,
            cursor: raw.trim() ? 'pointer' : 'default',
          }}
        >
          Распарсить
        </button>

        {parseError && (
          <div className="text-xs rounded p-2" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>
            {parseError}
          </div>
        )}

        {/* Preview */}
        {parsed && (
          <div className="flex flex-col gap-2 rounded-lg p-3" style={{ background: 'var(--background)', border: '1px solid var(--border)' }}>
            <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Предпросмотр</div>
            <div className="grid gap-1" style={{ gridTemplateColumns: 'auto 1fr', rowGap: 4, columnGap: 12 }}>
              {[
                ['Тип', <span style={{ color: typeColor, fontWeight: 700 }}>{parsed.trade_type}</span>],
                ['Биржа', parsed.exchange],
                ['Курс', `${parsed.price.toFixed(2)} UAH`],
                ['Кол-во USDT', `${parsed.amount_usdt.toFixed(2)} USDT`],
                ['Сумма UAH', `${parsed.amount_uah.toFixed(2)} ₴`],
                ['Банк', parsed.bank ?? '—'],
                ['Дата (Киев)', formatDate(parsed.executed_at)],
              ].map(([label, value]) => (
                <>
                  <span key={`l-${label}`} className="text-xs" style={{ color: 'var(--muted)' }}>{label}</span>
                  <span key={`v-${label}`} className="text-xs" style={{ color: 'var(--text)' }}>{value}</span>
                </>
              ))}
            </div>

            {/* Extra fields */}
            <div className="flex flex-col gap-2 mt-1">
              <div className="flex flex-col gap-1">
                <label className="text-xs" style={{ color: 'var(--muted)' }}>Контрагент (опционально)</label>
                <input
                  value={counterparty}
                  onChange={(e) => setCounterparty(e.target.value)}
                  placeholder="Ник на бирже"
                  style={inputStyle}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs" style={{ color: 'var(--muted)' }}>Комментарий (опционально)</label>
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Заметка к сделке"
                  style={inputStyle}
                />
              </div>
            </div>
          </div>
        )}

        {saveError && (
          <div className="text-xs rounded p-2" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>
            {saveError}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            style={{
              background: 'transparent', border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--muted)',
              padding: '7px 16px', fontSize: 13, cursor: 'pointer',
            }}
          >
            Отмена
          </button>
          <button
            onClick={handleSave}
            disabled={!parsed || saving}
            style={{
              background: parsed && !saving ? 'var(--accent)' : 'var(--border)',
              color: parsed && !saving ? '#000' : 'var(--muted)',
              border: 'none', borderRadius: 8,
              padding: '7px 16px', fontSize: 13, fontWeight: 600,
              cursor: parsed && !saving ? 'pointer' : 'default',
            }}
          >
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  )
}
