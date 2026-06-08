"""AI-агент: аналитик P2P-торговли через Anthropic API (httpx, без SDK)."""
from __future__ import annotations

from typing import Any

import httpx

from config.settings import settings

_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT = 30.0

_SYSTEM_PROMPT = """\
Ты — опытный напарник по P2P-торговле USDT/UAH (Binance, Bybit). Не бот-бухгалтер, а живой собеседник: говоришь нормальным человеческим языком, как коллега скинул бы мысли в телеге. Без канцелярита, без жирных заголовков, без нумерованных списков — просто связный разговорный текст.

Что делаешь: разбираешь данные вдумчиво, рассуждаешь вслух, подсвечиваешь паттерны и то, на что стоит посмотреть. Не сухие цифры, а их смысл: где курс относительно истории, что с спредом, на какой фазе рынок, что это исторически значило.

Чего НЕ делаешь: не даёшь прямых сигналов на вход — ни «покупай», ни «продавай», ни «сейчас хорошее время для входа», ни «хорошие условия для покупки». Это всё торговые сигналы, просто в разной обёртке — тебе они запрещены. Ты не предсказываешь будущее: ты видишь только историю курса, но не знаешь новостей, глобального движения крипты и ликвидности мейкеров. Поэтому честно оговаривай, где твоя картина неполная и где «так было раньше» — это не гарантия, что так будет.

Как подсвечивать с пользой, но без сигнала — пример правильного тона:
«Курс сейчас в нижней трети месячного диапазона, спред шире обычного. Исторически в похожих точках спред потом сужался — но это прошлое, не обещание. На что я бы посмотрел на твоём месте: [факторы]. Решать тебе.»

Валюта только ₴ и $, рубли не упоминать никогда. Время — Киев. Пиши по-русски, живо, по делу, без воды.\
"""


class AIServiceError(Exception):
    """Базовое исключение AI-сервиса."""


class AIKeyMissingError(AIServiceError):
    """ANTHROPIC_API_KEY не задан в конфиге."""


class AIResponseError(AIServiceError):
    """API вернул ошибку или невалидный ответ."""


def _require_key() -> str:
    key = settings.anthropic_api_key
    if not key:
        raise AIKeyMissingError(
            "ANTHROPIC_API_KEY не задан. Добавь его в config/.env."
        )
    return key


# ── Построение user-сообщения по режиму ──────────────────────────────────────

def _build_sessions_message(payload: dict[str, Any]) -> str:
    """
    payload ожидает:
      sessions: list[dict]  — последние N сессий (SessionOut-поля)
      trades:   list[dict]  — сделки активной или последней сессии (TradeOut-поля)
      market:   dict        — {"buy_price": float, "sell_price": float} текущий рынок
    """
    lines: list[str] = ["## Торговые сессии\n"]

    sessions: list[dict] = payload.get("sessions", [])
    if not sessions:
        lines.append("Сессий пока нет.\n")
    else:
        for s in sessions:
            status = s.get("status", "?")
            num = s.get("number", "?")
            capital = s.get("start_capital_uah", 0)
            realized = s.get("realized_uah")
            unrealized = s.get("unrealized_uah")
            remaining = s.get("usdt_remaining")
            trade_count = s.get("trade_count", 0)
            started = s.get("started_at", "?")
            closed = s.get("closed_at")
            close_price = s.get("close_sell_price")

            lines.append(f"### Сессия №{num} [{status.upper()}]")
            lines.append(f"- Старт капитала: ₴{capital:,.0f}")
            lines.append(f"- Сделок: {trade_count}")
            lines.append(f"- Начата: {started}")
            if closed:
                lines.append(f"- Закрыта: {closed}")
            if close_price:
                lines.append(f"- Курс закрытия: ₴{close_price:.2f}")
            if realized is not None:
                lines.append(f"- Реализованный P&L: ₴{realized:+.2f}")
            if unrealized is not None:
                lines.append(f"- Нереализованный P&L: ₴{unrealized:+.2f}")
            if remaining is not None:
                lines.append(f"- Остаток USDT: ${remaining:.2f}")
            lines.append("")

    trades: list[dict] = payload.get("trades", [])
    if trades:
        lines.append("## Сделки текущей сессии\n")
        buys = [t for t in trades if t.get("trade_type") == "BUY"]
        sells = [t for t in trades if t.get("trade_type") == "SELL"]
        total_usdt_bought = sum(t.get("amount_usdt", 0) for t in buys)
        total_uah_spent = sum(t.get("amount_uah", 0) for t in buys)
        total_usdt_sold = sum(t.get("amount_usdt", 0) for t in sells)
        total_uah_received = sum(t.get("amount_uah", 0) for t in sells)
        avg_buy = (total_uah_spent / total_usdt_bought) if total_usdt_bought else None

        lines.append(f"- Покупок: {len(buys)} шт., куплено ${total_usdt_bought:.2f} за ₴{total_uah_spent:,.2f}")
        if avg_buy:
            lines.append(f"- Средняя цена покупки: ₴{avg_buy:.2f}")
        lines.append(f"- Продаж: {len(sells)} шт., продано ${total_usdt_sold:.2f} за ₴{total_uah_received:,.2f}")

        lines.append("\nДетали сделок:")
        for t in trades:
            ttype = t.get("trade_type", "?")
            price = t.get("price", 0)
            usdt = t.get("amount_usdt", 0)
            uah = t.get("amount_uah", 0)
            bank = t.get("bank") or "—"
            at = str(t.get("executed_at", "?"))[:16]
            lines.append(f"  [{ttype}] ₴{price:.2f} × ${usdt:.2f} = ₴{uah:.2f} | банк: {bank} | {at}")
        lines.append("")

    market: dict = payload.get("market", {})
    if market:
        lines.append("## Текущий рынок (Binance USDT/UAH)")
        buy_p = market.get("buy_price")
        sell_p = market.get("sell_price")
        if buy_p:
            lines.append(f"- BUY (лучшая цена покупки): ₴{buy_p:.2f}")
        if sell_p:
            lines.append(f"- SELL (лучшая цена продажи): ₴{sell_p:.2f}")
        if buy_p and sell_p:
            spread = sell_p - buy_p
            lines.append(f"- Спред BUY→SELL: ₴{spread:.2f} ({spread / buy_p * 100:.2f}%)")

    lines.append("\nПроанализируй сессию(и) и дай краткий комментарий трейдеру.")
    return "\n".join(lines)


def _build_market_message(payload: dict[str, Any]) -> str:
    """
    payload ожидает:
      summary: dict  — {exchange, pair, period_label, point_count,
                         buy: {current, min_p, max_p, avg_p, position_pct, phase},
                         sell: {current, min_p, max_p, avg_p},
                         spread: {current, avg_p, vs_avg}}
      chart:   list[dict]  — точки {ts, buy_price, sell_price}
      note:    str | отсутствует  — сообщение если данных недостаточно
    """
    lines: list[str] = ["## Рыночная аналитика USDT/UAH\n"]

    note = payload.get("note")
    if note:
        lines.append(f"⚠️ {note}")
        lines.append("\nПрокомментируй ситуацию кратко.")
        return "\n".join(lines)

    s: dict = payload.get("summary") or {}
    if s:
        exch = s.get("exchange", "н/д").upper()
        pair = s.get("pair", "н/д")
        period_label = s.get("period_label", "н/д")
        lines.append(f"Биржа: {exch} | Пара: {pair} | Горизонт: {period_label}\n")

        buy: dict = s.get("buy") or {}
        if buy:
            lines.append("### BUY (покупаем USDT)")
            cur = buy.get("current")
            bmin = buy.get("min_p")
            bmax = buy.get("max_p")
            bavg = buy.get("avg_p")
            pct = buy.get("position_pct")
            phase = buy.get("phase", "н/д")
            if cur is not None:
                lines.append(f"- Текущий курс: ₴{cur:.2f}")
            if bmin is not None and bmax is not None:
                lines.append(f"- Диапазон за {period_label}: ₴{bmin:.2f} – ₴{bmax:.2f}")
            if bavg is not None:
                lines.append(f"- Средний за {period_label}: ₴{bavg:.2f}")
            if pct is not None:
                lines.append(f"- Позиция в диапазоне: {pct:.1f}% ({phase})")
            lines.append("")

        sell: dict = s.get("sell") or {}
        if sell:
            lines.append("### SELL (продаём USDT)")
            cur = sell.get("current")
            smin = sell.get("min_p")
            smax = sell.get("max_p")
            savg = sell.get("avg_p")
            if cur is not None:
                lines.append(f"- Текущий курс: ₴{cur:.2f}")
            if smin is not None and smax is not None:
                lines.append(f"- Диапазон за {period_label}: ₴{smin:.2f} – ₴{smax:.2f}")
            if savg is not None:
                lines.append(f"- Средний за {period_label}: ₴{savg:.2f}")
            lines.append("")

        spread: dict = s.get("spread") or {}
        if spread:
            lines.append("### Спред BUY→SELL")
            cur = spread.get("current")
            avg = spread.get("avg_p")
            vs = spread.get("vs_avg")
            if cur is not None:
                lines.append(f"- Текущий: ₴{cur:.2f}")
            if avg is not None:
                lines.append(f"- Средний за {period_label}: ₴{avg:.2f}")
            if vs is not None:
                sign = "+" if vs >= 0 else ""
                lines.append(f"- Отклонение от среднего: {sign}₴{vs:.2f}")
            lines.append("")

    chart: list[dict] = payload.get("chart", [])
    if chart:
        period_label = (payload.get("summary") or {}).get("period_label", "")
        header = f"### Ценовой ряд ({len(chart)} точек за {period_label}, хронологически)\n" if period_label else f"### Ценовой ряд ({len(chart)} точек, хронологически)\n"
        lines.append(header)
        lines.append("ts_unix | BUY ₴ | SELL ₴")
        for pt in chart[-24:]:
            ts = pt.get("ts", "?")
            buy_p = pt.get("buy_price", 0)
            sell_p = pt.get("sell_price", 0)
            lines.append(f"{ts} | {buy_p:.2f} | {sell_p:.2f}")
        lines.append("")

    lines.append("Прокомментируй текущую рыночную ситуацию кратко.")
    return "\n".join(lines)


_MESSAGE_BUILDERS = {
    "sessions": _build_sessions_message,
    "market": _build_market_message,
}


# ── Основная функция ──────────────────────────────────────────────────────────

async def analyze(mode: str, payload: dict[str, Any]) -> str:
    """
    Вызывает Anthropic API и возвращает текст комментария агента.

    mode:    "sessions" | "market"
    payload: данные для анализа (см. _build_*_message)

    Raises:
        AIKeyMissingError  — ключ не задан в конфиге
        AIServiceError     — ошибка API или таймаут
    """
    if mode not in _MESSAGE_BUILDERS:
        raise AIServiceError(f"Неизвестный режим агента: {mode!r}. Допустимо: {list(_MESSAGE_BUILDERS)}")

    api_key = _require_key()
    user_message = _MESSAGE_BUILDERS[mode](payload)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    body = {
        "model": settings.anthropic_model,
        "max_tokens": 1024,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(_API_URL, headers=headers, json=body)
    except httpx.TimeoutException:
        raise AIServiceError("Anthropic API не ответил за 30 секунд. Попробуй позже.")
    except httpx.RequestError as exc:
        raise AIServiceError(f"Ошибка сети при запросе к Anthropic: {exc}")

    if response.status_code == 401:
        raise AIServiceError("Anthropic API: неверный ключ (401). Проверь ANTHROPIC_API_KEY в config/.env.")
    if response.status_code == 429:
        raise AIServiceError("Anthropic API: превышен лимит запросов (429). Подожди немного.")
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message", response.text[:200])
        except Exception:
            detail = response.text[:200]
        raise AIResponseError(f"Anthropic API вернул {response.status_code}: {detail}")

    try:
        data = response.json()
        text = data["content"][0]["text"]
        return text
    except (KeyError, IndexError, ValueError) as exc:
        raise AIResponseError(f"Неожиданный формат ответа Anthropic: {exc}. Тело: {response.text[:300]}")
