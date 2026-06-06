# Контекст проекта p2p-system

## Что готово

- Структура проекта (core/, modules/, data/, config/, logs/, scripts/)
- Конфиг: config/settings.py + config/.env (pydantic-settings, extra="ignore")
- Логгер: core/utils/logger.py → get_logger()
- main.py — приветствие + проверка data/p2p.db
- Слой БД: core/database/ (base.py, models.py, db_init.py, __init__.py)
  - Модели: Maker / Snapshot / Order (SQLAlchemy 2.0, Mapped[], relationships)
  - Maker: external_id + UniqueConstraint(exchange, external_id), total_orders, completion_rate, is_merchant, first_seen, last_seen
  - Snapshot: asset, fiat, trade_type, is_deep, collected_at, order_count
  - engine + get_session (contextmanager) + init_db()
- scripts/init_db.py — создаёт data/p2p.db
- core/exchanges/binance.py — BinanceP2PClient + BinanceP2POrder (external_id из userNo)
  - Пагинация: rows > 20 → несколько запросов по 20 (Binance API max = 20/страница)
  - Deep snapshot (rows=100) работает через 5 страниц
- core/exchanges/bybit.py — BybitP2PClient + BybitP2POrder (external_id из userId)
- core/utils/timezone.py — now_kyiv(), to_kyiv(), format_kyiv(); БД хранит UTC, всё отображение в Europe/Kyiv
- modules/tracker/collector.py — Collector с БД-интеграцией (UPSERT Maker → Snapshot → Orders), логи в Europe/Kyiv
- modules/tracker/__init__.py — run_tracker() (BlockingScheduler, timezone=Europe/Kyiv)
- scripts/run_tracker.py — точка входа трекера
- scripts/check_db.py — утилита проверки БД (мейкеры, снимки, ордера, топ-3), время в Киеве
- scripts/clear_db.py — очистка всех таблиц с подтверждением (DELETE orders → snapshots → makers)
- scripts/market.py — просмотрщик данных, 5 подкоманд (argparse git-style):
  - `summary [--hours N]` — сводка по всем парам: снимки, мин/макс/avg/сейчас + спреды BN↔BB
  - `chart PAIR [--hours N] [--side BUY/SELL/BOTH]` — ASCII multi-line график цены (топ-1 ордер по снимкам)
  - `spread PAIR [--hours N]` — динамика и статистика спреда Binance↔Bybit (BUY+SELL)
  - `makers PAIR [--side] [--top N] [--exchange]` — топ мейкеров по появлениям, avg/best цена
  - `latest` — текущий снимок всех 8 пар, топ-5 ордеров каждой
- scripts/start_tracker.bat — запуск трекера (fallback, отдельное окно)
- scripts/start_tracker_background.ps1 — вызывается из .bat, настраивает окружение
- scripts/stop_tracker.ps1 — аварийная остановка по PID
- data/p2p_backup_20260501_morning.db — бэкап первой ночи сбора (3312 снимков, 66394 ордеров)
- **Шаг 1 завершён:** фильтр выбросов + внутрибиржевой спред + команда outliers
  - core/utils/outliers.py — функции median_price, is_outlier, filter_outliers, get_clean_top1 (threshold 10%)
  - scripts/market.py — все команды по умолчанию работают с очищенными данными, флаг --raw для сырых; в summary секция "Внутрибиржевой спред (BUY vs SELL)"
  - Новая команда: python scripts/market.py outliers [--hours N] [--pair X/Y] [--side BUY/SELL]
  - Проверено на живой БД: Quentin777111 (42.10) и fast_retrade (42.00) корректно отфильтровываются
  - 12 мая: фильтр смягчён с 2.5% до 10% — отрезаются только жёсткие ловушки
  - 12 мая: удалены торговые ярлыки 1_BUY_USDT.bat, 2_SELL_USDT.bat; остался 3_MARKET.bat
- **Шаг 2 завершён:** банки + надёжность мейкеров + команда find
  - core/banks/registry.py — справочник украинских банков (30+ записей): SAFE / CAUTION / AVOID; Bybit ID маппинг + Binance text patterns
  - core/utils/maker_trust.py — классификация EXPERT ★ / NORMAL · / NOVICE ! / UNKNOWN ? + значок ⊕ для merchant
  - scripts/market.py latest — колонка "Банк" с цветной подсветкой + метки надёжности у никнейма
  - НОВАЯ команда: python scripts/market.py find PAIR --side BUY/SELL [--bank NAME] [--avoid-banks N1,N2] [--min-orders N] [--min-completion N] [--exchange E] [--top N] [--raw]
- **Шаг 3 завершён:** FastAPI бэкенд
  - api/ — FastAPI приложение (main.py, routers/, schemas/)
  - Эндпоинты: GET /api/health, /api/market/orders, /api/market/chart, /api/market/summary, /api/market/makers, /api/market/banks
  - Pydantic-схемы для всех ответов
  - CORS настроен (localhost:5173)
  - scripts/start_api.bat — запуск uvicorn (fallback)
  - Документация: http://localhost:8000/docs (Swagger UI)
- **Шаг 4 завершён:** React фронтенд
  - 4А — каркас Vite + React + TypeScript + Tailwind CSS + shadcn/ui; тёмная тема в стиле Bybit
  - 4Б — главный layout + живой график USDT/UAH (Recharts, реальные данные из API)
  - 4В — таблица ордеров с цветной разметкой банков, метками надёжности мейкеров, пагинацией
  - Полировка: выравнивание высот блоков (items-start), отключение автоперевода Chrome (translate="no" + notranslate meta)
  - scripts/start_frontend.bat — запуск Vite dev server (fallback)
- **Шаг 5 завершён:** Trade Journal
  - 5А — бэкенд: модель Trade (core/database/models.py), 5 endpoints в api/routers/trades.py:
    POST /api/trades, GET /api/trades (с фильтрами), GET /api/trades/stats, GET /api/trades/{id}, DELETE /api/trades/{id}
  - 5Б — фронтенд: TradesHistory (таблица сделок, UTC→Kyiv), AddTradeModal (textarea → парсер → превью → сохранение),
    binanceParser.ts (парсит текст страницы сделки Binance, конвертирует время Kyiv→UTC)
  - 5В — страница статистики: react-router-dom, Header с NavLink, pages/Dashboard, pages/Statistics
    Статистика: селектор периода (7д/30д/всё время), карточка P&L, сетка 4 метрик, заглушка при 0 сделок
- **Шаг 7А завершён:** GET /api/market/opportunities — поиск выгодных ордеров по позиции
  - api/services/market_service.py → get_opportunities(); api/routers/market.py → /opportunities
  - Авто-режим: usdt_balance > 0 → exit (продажа), иначе → entry (покупка)
  - entry: медиана топ-5 BUY ордеров, порог = reference * (1 - 0.3%), фильтр NORMAL+, только SAFE банки
  - exit: break_even из истории сделок, порог = break_even + 0.3 ₴/USDT
- **Шаг 7Б завершён:** визуализация точек возможностей на PriceChart
  - frontend/src/components/PriceChart.tsx — DotsLayer (Recharts v3 хуки useYAxisScale/usePlotArea)
  - Кружки на правом краю графика: зелёные (exit) / оранжевые (entry), радиус 4–10px ∝ profit
  - OppTooltip (fixed-position): никнейм+★, уровень/сделки/%, цена, объём, лимиты, банки, прибыль ₴/USDT
  - YAxis domain расширяется чтобы вместить цены ордеров; тултип переворачивается у правого края экрана
  - Индикатор режима под ценой: "Режим: вход/выход" + "Порог: X.XX ₴"
- **Шаг 7В (7Б часть 2) завершён:** фильтр по объёму + вторая линия рынка + маркеры сделок
  - volume_uah фильтр на /api/market/chart и /api/market/opportunities (min_amount ≤ volume_uah)
  - UI: input + чипы 1k/5k/25k/100k/Любой, debounce 300ms, индикатор "Объём: X ₴"
  - Вторая линия "Общий рынок" (серая пунктирная) когда volume filter активен
  - TradesLayer: SVG маркеры сделок на графике (BUY=зелёный▲ снизу, SELL=красный▼ сверху)
  - X-позиция по линейной интерполяции timestamp ∈ [minTime, maxTime] chart points
  - TradeTooltip: тип/цена/USDT/UAH/контрагент/банк/время
  - Legend: кастомный content — линии для chart series + кружки для Покупки/Продажи
  - Маркеры фильтруются по hours и exchange (не по volume)

## Архитектура проекта

```
p2p-system/
├── api/                        # FastAPI бэкенд (Шаг 3)
│   ├── main.py                 # приложение, CORS, подключение роутеров
│   ├── routers/                # маршруты: health, info, market, makers, banks, trades
│   └── schemas/                # Pydantic-модели ответов (incl. TradeCreate, TradeOut, TradeStats)
├── core/
│   ├── banks/registry.py       # справочник банков
│   ├── database/               # SQLAlchemy: base, models (Maker/Snapshot/Order/Trade), db_init
│   ├── exchanges/              # binance.py, bybit.py
│   └── utils/                  # logger, timezone, outliers, maker_trust
├── frontend/                   # React фронтенд (Шаг 4)
│   ├── index.html              # translate="no" — отключён автоперевод Chrome
│   └── src/
│       ├── App.tsx             # BrowserRouter + Routes (/, /stats) + Header
│       ├── lib/
│       │   ├── api.ts          # axios-клиент + типы Trade/TradeStats, fetchTrades/createTrade/deleteTrade/fetchTradeStats
│       │   └── binanceParser.ts # парсер текста страницы сделки Binance → TradeCreate
│       ├── pages/
│       │   ├── Dashboard.tsx   # дашборд (график + ордера + история + AI-заглушка)
│       │   └── Statistics.tsx  # статистика: P&L + 4 метрики + селектор периода
│       └── components/
│           ├── Header.tsx          # общий хедер: лого + NavLink навигация + API-индикатор
│           ├── PriceChart.tsx      # график USDT/UAH (lightweight-charts v5), ТФ 6Ч-3М
│           ├── PositionBar.tsx     # строка позиции + управление сессией (старт/закрытие/отчёт)
│           ├── SessionsSummary.tsx # карточка «Общий учёт по сессиям» (P&L по закрытым)
│           ├── TradesHistory.tsx   # журнал сделок, сгруппированный по сессиям
│           ├── TrackerHealthWidget.tsx # виджет состояния трекера
│           ├── AddTradeModal.tsx   # модалка добавления сделки через буфер обмена
│           └── ui/                 # shadcn/ui компоненты (Table и др.)
├── modules/tracker/            # сборщик (APScheduler)
├── scripts/                    # точки входа + .bat-файлы
├── config/                     # settings.py, .env
├── data/                       # p2p.db
├── logs/                       # general.log, errors.log
└── start_all.bat               # ГЛАВНЫЙ ЗАПУСК — все 5 окон сразу
```

## Workflow — запуск проекта

### Основной способ — двойной клик на `start_all.bat` в корне
Открывает 5 окон PowerShell сразу:
1. **Tracker** — сборщик данных (APScheduler)
2. **API** — FastAPI + uvicorn на localhost:8000
3. **Frontend** — Vite dev server на localhost:5173
4. **Claude Code** — AI-помощник в терминале
5. **Workspace** — рабочий терминал для команд

### Fallback — отдельные .bat (если нужно запустить по одному)
- `scripts/start_tracker.bat` — только трекер
- `scripts/start_api.bat` — только API
- `scripts/start_frontend.bat` — только фронтенд

### Команды для анализа данных (в окне Workspace)
```powershell
$env:PYTHONUTF8=1
.\venv\Scripts\python.exe -m scripts.market summary
.\venv\Scripts\python.exe -m scripts.market latest
.\venv\Scripts\python.exe -m scripts.market find USDT/UAH --side BUY --bank Monobank
.\venv\Scripts\python.exe -m scripts.market chart USDT/UAH --hours 24
```

## Инструменты разработки

- **Playwright MCP** подключён к Claude Code — можно попросить Claude смотреть на браузер в реальном времени. Фраза: _"используй playwright mcp"_ или _"проверь через playwright mcp"_. Умеет: навигация, снимки DOM, JS-eval, клики, скриншоты.

## Стек

| Слой | Технология | Статус |
|------|-----------|--------|
| Сборщик | Python + httpx + APScheduler | готов (Шаги 1–2) |
| БД | SQLite → PostgreSQL, SQLAlchemy 2.0 | готов |
| Бэкенд | FastAPI + uvicorn | готов (Шаги 3, 7А, 8А, сессии 1A+1B) |
| Фронтенд | Vite + React + TypeScript + Tailwind + shadcn | готов (Шаги 4–8В, сессии ч.2+3) |
| Чарт библиотека | lightweight-charts v5 | готов (Шаг 8Б), ТФ 6Ч/12Ч/24Ч/7Д/1М/3М |
| Trade Journal | учёт сделок, журнал по сессиям, статистика | готов (Шаг 5 + сессии 1A–3) |
| Алерты | Telegram Bot API | планируется |
| AI-агент | Claude API | планируется (Шаг 9) |

## Последний коммит

`9d281ed Feat: timeframes 6H/12H/24H/7D/1M/3M (add 6h/12h, remove 6m/1y)`

## Роадмап

- ✅ Шаг 1 — Фильтр выбросов + спред + outliers
- ✅ Шаг 2 — Банки + надёжность мейкеров + find
- ✅ Шаг 3 — FastAPI бэкенд
- ✅ Шаг 4 — Web-интерфейс (живой график + таблица ордеров)
- ✅ Шаг 5 — Trade Journal (5А backend, 5Б frontend, 5В статистика — всё готово)
- ✅ Шаг 7А — GET /api/market/opportunities с автоопределением режима по позиции
- ✅ Шаг 7Б — визуализация точек возможностей на графике (DotsLayer + OppTooltip)
- ✅ Шаг 7В — фильтр объёма + двойная линия рынка + маркеры сделок на графике (TradesLayer + TradeTooltip)
- ✅ Шаг 8А — агрегация графика по таймфреймам + обе стороны рынка одновременно (b526368)
- ✅ Шаг 8Б — PriceChart.tsx переписан на lightweight-charts v5: две линии BUY/SELL, сглаживание Curved, таймфреймы, ResizeObserver
- ✅ Удаление сделок — кнопка корзины + AlertDialog подтверждения в блоке История (fcdef7c)
- ✅ Шаг 8В часть 1 — фильтр `volume_uah` на графике (VPS), тумблеры слоёв (Сделки ON / Коридор+Возможности disabled-каркас), метки сделок `createSeriesMarkers` v5, тултип по `hoveredObjectId` (ad3c752)
- ✅ Шаг 8В часть 2 — коридор 25/75 заливкой (BandPrimitive), точки opportunities (OpportunitiesPrimitive), оба через `attachPrimitive`, hitTest + тултип (285fa9e)
  - **Шаг 8 ЗАКРЫТ ПОЛНОСТЬЮ**
- ✅ Торговые сессии 1A — таблица `sessions` (11 полей) + `session_id FK` в `trades`. Миграция `create_all` + ручной `ALTER TABLE`. Бэкап локальной БД сделан. (18827a8)
- ✅ Торговые сессии 1B — `api/routers/sessions.py`: 5 эндпоинтов, P&L по средневзвешенной формуле из `pnl.py`, автопривязка сделок, защита от нулевого курса → 503. Проверено curl: `realized_uah = +64`. (8506a3a)
- ✅ Торговые сессии — Миграция VPS (6 июня 2026) — на боевой базе создана таблица `sessions` через `create_all` + добавлена колонка `session_id` через `ALTER TABLE`. Данные не пострадали (trades/snapshots целы). Бэкапы: `p2p_backup_pre_sessions.db` и `p2p_backup_before_session_cleanup.db`. Тестовые сессии (№1-3) очищены — следующая реальная будет №1.
- ✅ Торговые сессии — Часть 2 (фронт, 6 июня 2026):
  - `frontend/src/lib/api.ts`: интерфейс `SessionOut` + `fetchActiveSession`, `startSession`, `closeSession`. `closeSession` НЕ передаёт курс с фронта — бэкенд берёт его сам (защита от подделки P&L). 503 обрабатывается: диалог остаётся открытым, сессия активна, пользователь видит причину.
  - `frontend/src/components/PositionBar.tsx`: компактная горизонтальная строка слева — форма старта (Капитал ₴ + биржа + кнопка «Старт»), шапка активной сессии (номер / капитал / время / биржа / кнопка «Закрыть»), диалог подтверждения закрытия, карточка отчёта (реализовано «живые деньги» / нереализовано «бумажная оценка» / итого / длительность / сделок). Состояние переживает перезагрузку страницы через `fetchActiveSession`.
  - Коммиты: `9d30d2c` (PositionBar компоновка), `2c4e8d0` (api.ts функции сессий)
- ✅ **Торговые сессии — Часть 3 (журнал+учёт, 6 июня 2026) — f2cbcef:**
  - `TradesHistory.tsx` переписан: плоский список → раскрываемые группы по сессиям. Заголовок группы: «Сессия №N · активна/закрыта · +реализовано ₴ · N сделок». Активная сессия разворачивается по умолчанию. Сделки с `session_id = null` → группа «Вне сессии» внизу. Удаление корзиной работает. Пустые состояния сохранены.
  - Новый компонент `SessionsSummary.tsx`: карточка «Общий учёт по сессиям» — закрыто сессий, суммарно реализовано (зелёный/красный, пометка «живые деньги»), суммарно нереализовано (если есть). Данные считаются на фронте из `GET /api/sessions` — бэкенд не трогали. При отсутствии закрытых сессий — «Пока нет закрытых сессий».
  - `api.ts`: добавлен `session_id: number | null` в `interface Trade`; добавлена `fetchSessions()` → `GET /api/sessions`.
  - **Торговые сессии ЗАКРЫТЫ ПОЛНОСТЬЮ** (1A → 1B → миграция VPS → часть 2 → часть 3).
- ✅ **Чистка боевой базы (6 июня 2026):** удалены тестовая сессия №1 и 4 мартовских сделки (id 1-4, 11.03.2026). Бэкап перед удалением: `p2p_backup_before_test_cleanup.db` (133 МБ). Итог: `trades=0`, `sessions=0`, `snapshots=~49700` — целы. Реальная история начнётся с сессии №1 с чистого листа.
- ✅ **Таймфреймы графика (6 июня 2026) — 9d281ed:** набор кнопок изменён на 6Ч / 12Ч / 24Ч / 7Д / 1М / 3М. Добавлены `6h` (bucket 1 мин) и `12h` (bucket 2 мин), убраны `6m` и `1y`. Задеплоено. Проверено: 6h=307 точек шаг 1 мин, 12h=361 точка шаг 2 мин, `6m` → 422, `/timeframes` → `available=[6h,12h,24h]`.

### ⚠ Хвосты (не баги — нет данных для проверки вживую)
- Метки сделок: журнал пуст, проверить при первой реальной сделке (нужна стрелка на нужном ТФ с нужной ценой)
- Точки opportunities: рынок выше порога входа, появятся при предложении ниже threshold
- На отфильтрованных объёмах (5к+) линии зубчатые — будущая задача (агрессивнее сглаживание / шире окно агрегации)
- Очистка локальной БД — тестовые сессии от curl-тестов 1B; не срочно (локалка в бой не идёт)

### Формула P&L (зафиксирована, проверена)

```
avg_buy_price  = total_uah_spent / total_usdt_bought     # средневзвешенная
realized_uah   = uah_received − usdt_sold × avg_buy_price
unrealized_uah = usdt_remaining × (current_sell_price − avg_buy_price)
total_pnl      = realized_uah + unrealized_uah            # фиксируется при закрытии навсегда
```

Курс закрытия берёт бэкенд сам (фронт не передаёт — защита от подделки P&L). Не путать с `TradeStats` (там другой расчёт — не использовать для сессий).

### Далее (по приоритету)
- Шаг 9 — AI-агент: начать с аналитика-комментатора (позиция + рыночная ситуация → Anthropic API → текстовый разбор). Не горит — нужна накопленная история сессий.
- Telegram-алерты (пороговые уведомления по цене/спреду)
- Миграция SQLite → PostgreSQL

## Workflow импорта сделок (Trade Journal)

1. Открой страницу сделки на Binance (раздел P2P → История → детали конкретного ордера)
2. Скопируй блок с деталями: от строки "Номер ордера" до строки "Способ оплаты" (включительно)
3. На дашборде http://localhost:5173 в блоке **"История"** нажми **"+ Добавить"**
4. Вставь скопированный текст в поле, нажми **"Распарсить"**
5. Проверь превью (тип, курс, USDT, UAH, банк, дата в Киевском времени)
6. Опционально заполни "Контрагент" и "Комментарий"
7. Нажми **"Сохранить"** — сделка появится в таблице

Парсер понимает оба варианта написания: "КупитьUSDT" и "Купить USDT", "ПродатьUSDT" и "Продать USDT".
Время со страницы Binance — это Kyiv-время, парсер конвертирует в UTC перед сохранением в БД.
В таблице история отображается обратно в Kyiv-времени (те же цифры что на бирже).

## Workflow обновления документации

После завершения каждого Шага плана обновляются ОБА файла:
- PROJECT_CONTEXT.md — в "Что готово" добавить новые компоненты, обновить роадмап
- CHEATSHEET.md — добавить новые пользовательские команды, убрать устаревшие

## Известные аномалии в данных

В текущем датасете обнаружены систематические ловчие ордера:
- USDT/UAH BUY на Binance: мейкер Quentin777111 держит ордер 42.10 при рыночной цене ~43.50 (объём 10 USDT, 4-й день подряд)
- USDT/UAH BUY на Bybit: fast_retrade ставит 42.00 на объём 3 USDT
- USDC/UAH BUY на Binance: периодически появляются ордера с ценой до 90 UAH

Эти кейсы — основная мотивация для Шага 1 (фильтр выбросов).
