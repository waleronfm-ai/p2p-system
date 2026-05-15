import type { TradeCreate } from './api'

export interface ParsedTrade extends Omit<TradeCreate, 'counterparty' | 'note'> {}

function extractAfter(text: string, label: string): string | null {
  const idx = text.indexOf(label)
  if (idx === -1) return null
  return text.slice(idx + label.length).trimStart()
}

function firstToken(s: string): string {
  return s.split(/\s+/)[0] ?? ''
}

function parseUah(raw: string): number | null {
  // "₴ 3,784.44" or "3,784.44" — commas are thousands separators
  const cleaned = raw.replace(/[₴\s]/g, '').replace(/,/g, '')
  const n = parseFloat(cleaned)
  return isNaN(n) ? null : n
}

function parseFloat2(raw: string): number | null {
  const cleaned = raw.replace(/,/g, '')
  const n = parseFloat(cleaned)
  return isNaN(n) ? null : n
}

// Kyiv offset in minutes: UTC+2 in winter, UTC+3 in summer (DST)
function kyivToUtcISO(localStr: string): string {
  // localStr: "YYYY-MM-DD HH:MM:SS"
  const [datePart, timePart] = localStr.trim().split(' ')
  const [year, month, day] = datePart.split('-').map(Number)
  const [hour, min, sec] = timePart.split(':').map(Number)

  // Use Intl to determine real offset for that date in Europe/Kyiv
  const localMs = Date.UTC(year, month - 1, day, hour, min, sec)
  const probe = new Date(localMs)
  const kyivStr = probe.toLocaleString('en-CA', { timeZone: 'Europe/Kyiv', hour12: false })
  // kyivStr: "YYYY-MM-DD, HH:MM:SS"
  const [kDate, kTime] = kyivStr.split(', ')
  const [ky, km, kd] = kDate.split('-').map(Number)
  const [kh, kmin, ks] = kTime.replace('24:', '00:').split(':').map(Number)
  const kyivProbeMs = Date.UTC(ky, km - 1, kd, kh, kmin, ks)
  const offsetMs = kyivProbeMs - localMs // positive when Kyiv is ahead of UTC
  const utcMs = localMs - offsetMs
  return new Date(utcMs).toISOString()
}

export function parseBinanceTrade(text: string): ParsedTrade | null {
  const t = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')

  // order_id — first sequence of 15+ digits
  const orderMatch = t.match(/\b(\d{15,})\b/)
  if (!orderMatch) return null
  const order_id = orderMatch[1]

  // trade_type
  let trade_type: 'BUY' | 'SELL' | null = null
  if (/Купить\s*USDT/i.test(t)) trade_type = 'BUY'
  else if (/Продать\s*USDT/i.test(t)) trade_type = 'SELL'
  if (!trade_type) return null

  // amount_uah — after "Сумма в фиате" then ₴ number
  const uahSection = extractAfter(t, 'Сумма в фиате')
  if (!uahSection) return null
  const uahMatch = uahSection.match(/₴\s*([\d,]+\.?\d*)/)
  if (!uahMatch) return null
  const amount_uah = parseUah(uahMatch[1])
  if (amount_uah === null) return null

  // price — after "Цена" then ₴ number
  const priceSection = extractAfter(t, 'Цена')
  if (!priceSection) return null
  const priceMatch = priceSection.match(/₴\s*([\d,]+\.?\d*)/)
  if (!priceMatch) return null
  const price = parseFloat2(priceMatch[1])
  if (price === null) return null

  // amount_usdt — after "Количество к получению" or "Общее кол-во", number before USDT
  let usdtSection = extractAfter(t, 'Количество к получению')
  if (!usdtSection) usdtSection = extractAfter(t, 'Общее кол-во')
  if (!usdtSection) return null
  const usdtMatch = usdtSection.match(/([\d,]+\.?\d*)\s*USDT/)
  if (!usdtMatch) return null
  const amount_usdt = parseFloat2(usdtMatch[1])
  if (amount_usdt === null) return null

  // executed_at — after "Время создания" YYYY-MM-DD HH:MM:SS
  const timeSection = extractAfter(t, 'Время создания')
  if (!timeSection) return null
  const timeMatch = timeSection.match(/(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/)
  if (!timeMatch) return null
  const executed_at = kyivToUtcISO(timeMatch[1])

  // bank — after "Способ оплаты", rest of trimmed line
  const bankSection = extractAfter(t, 'Способ оплаты')
  const bank = bankSection ? firstLine(bankSection).trim() || null : null

  return {
    exchange: 'binance',
    order_id,
    trade_type,
    price,
    amount_usdt,
    amount_uah,
    bank,
    executed_at,
  }
}

function firstLine(s: string): string {
  return s.split('\n')[0] ?? ''
}
