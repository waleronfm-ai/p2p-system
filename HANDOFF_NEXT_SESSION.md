# P2P Coach — Handoff для новой сессии (8 июня 2026)

## Что за проект

P2P Coach — дашборд для P2P-торговли USDT/UAH на Binance/Bybit.

- Бэкенд: Python / FastAPI / SQLite (`data/p2p.db`)
- Фронт: React / TypeScript / Tailwind CSS (локальный, смотрит на VPS API)
- Репо: github.com/waleronfm-ai/p2p-system
- Прод VPS: `185.223.57.171`, SSH порт `56777`, путь `/opt/p2p-system`

## Что ГОТОВО (не трогать, работает)

- **Трекер рынка** — работает 24/7 на VPS, `TrackerHealthWidget` на фронте
- **График** lightweight-charts v5: 2 линии BUY/SELL сглаженные; слои по тумблерам (метки сделок, коридор 25/75, opportunities); фильтр объёма; таймфреймы 6Ч / 12Ч / 24Ч / 7Д / 1М / 3М
- **Журнал сделок** — добавление, удаление, статистика, FAQ
- **Торговые сессии** — ПОЛНОСТЬЮ:
  - Старт / закрытие с отчётом P&L
  - Журнал группируется по сессиям с итогами
  - Общий суммарный учёт P&L
  - Формула P&L:
    - `avg_buy = uah_spent / usdt_bought`
    - `realized = uah_received − usdt_sold × avg_buy`
    - `unrealized = usdt_remaining × (current_sell − avg_buy)`
  - Курс закрытия сессии берёт **бэкенд** (не фронт)
- **Боевая база чистая** — `trades = 0`, `sessions = 0`; первая реальная сессия будет №1
- **AI-агент (Step 9)** — ПОЛНОСТЬЮ ГОТОВ И В ПРОДЕ:
  - Эндпоинт `POST /api/ai/analyze`, два режима: `sessions` (разбор сессий) и `market` (анализ рынка за 30 дней)
  - Модель: `claude-haiku-4-5`, переключается через `ANTHROPIC_MODEL` в `config/.env` на VPS
  - Кнопки «Разбор сессий» / «Рынок» на дашборде — loading/error/success состояния, защита от двойного клика
  - Ключ `ANTHROPIC_API_KEY` хранится только на бэкенде, фронт его не видит
  - Режим `sessions` возвращает статичное сообщение пока нет закрытых сессий (API не вызывается)

## Что ОСТАЛОСЬ

- **Первая реальная сессия ещё впереди** — база чистая (`sessions = 0`). Режим «Разбор сессий» заработает после закрытия первой сессии с реальными сделками.
- **Мелкий долг — рендер Markdown в AI-ответах**: агент отдаёт текст с Markdown-разметкой (`###`, `**`, `-`), фронт рендерит plain-text через `white-space: pre-wrap`. Варианты: добавить `react-markdown` на фронте ИЛИ добавить в system-prompt запрет Markdown. Не срочно, не мешает читаемости.
- Крупных незакрытых задач больше нет.

## Важные правила работы (соблюдать!)

- **Claude Code**: effort medium (НЕ max); не коммитить без явного «да»; промпты в код-блоках; в конце каждого промпта отчёт 3–5 строк
- **Миграции БД**: Alembic НЕТ. Новые таблицы — `create_all` авто. Новые колонки — вручную `ALTER TABLE` на VPS через `sqlite3`. ПЕРЕД любой миграцией боевой базы — **бэкап обязателен**.
- **Разрушающие операции** (DELETE и т.п.) — НЕ тестировать через Playwright-автокликер по боевой базе
- Если бэкенд менялся → нужен `deploy.bat` / деплой на VPS (фронт смотрит на прод)
- **Валюты**: только ₴ и $ (НИКОГДА рубли)
- **Время**: Киев / Europe/Kyiv (никогда Москва)
- У пользователя нет ноутбука — только стационарный ПК

## Последние коммиты

```
5f63d1b Fix: Step 9 — _build_market_message reads summary as dict (was iterating as list)
54358c7 Feat: Step 9 Part 3 — AI analysis buttons on dashboard (sessions/market modes)
428eca6 Feat: Step 9 Part 2 — AI router (/ai/analyze, X-Api-Key + rate limit, data collection)
6524a42 Docs: sessions Part 3 done, base cleanup, new timeframes (6 June)
9d281ed Feat: timeframes 6H/12H/24H/7D/1M/3M (add 6h/12h, remove 6m/1y)
```
