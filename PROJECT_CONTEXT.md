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
- **Шаг 5 (в работе):** Trade Journal
  - ✅ 5А — бэкенд: модель Trade (core/database/models.py), 5 endpoints в api/routers/trades.py:
    POST /api/trades, GET /api/trades (с фильтрами), GET /api/trades/stats, GET /api/trades/{id}, DELETE /api/trades/{id}
  - ✅ 5Б — фронтенд: TradesHistory (таблица сделок, UTC→Kyiv), AddTradeModal (textarea → парсер → превью → сохранение),
    binanceParser.ts (парсит текст страницы сделки Binance, конвертирует время Kyiv→UTC)
  - ⏳ 5В — страница статистики / P&L (ещё не делали)

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
│       ├── App.tsx             # главный layout, хедер, статус API
│       ├── lib/
│       │   ├── api.ts          # axios-клиент + типы Trade, fetchTrades/createTrade/deleteTrade
│       │   └── binanceParser.ts # парсер текста страницы сделки Binance → TradeCreate
│       └── components/
│           ├── PriceChart.tsx      # график USDT/UAH (Recharts)
│           ├── OrdersTable.tsx     # таблица ордеров с банками и надёжностью
│           ├── TradesHistory.tsx   # таблица сделок журнала (UTC→Kyiv)
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
| Бэкенд | FastAPI + uvicorn | готов (Шаг 3) |
| Фронтенд | Vite + React + TypeScript + Tailwind + shadcn | готов (Шаг 4) |
| Trade Journal | учёт сделок, история P&L | в работе (Шаг 5, 5А+5Б готовы) |
| Алерты | Telegram Bot API | планируется (Шаг 6) |
| AI-агент | Claude API | планируется (Шаги 7А–7В) |

## Последний коммит

`25fcce8 Step 5 part B: TradesHistory + AddTradeModal + Binance parser`

## Роадмап

- ✅ Шаг 1 — Фильтр выбросов + спред + outliers
- ✅ Шаг 2 — Банки + надёжность мейкеров + find
- ✅ Шаг 3 — FastAPI бэкенд
- ✅ Шаг 4 — Web-интерфейс (живой график + таблица ордеров)
- 🔄 Шаг 5 — Trade Journal (5А backend ✅, 5Б frontend ✅, 5В статистика ⏳)
- ⬜ Шаг 6 — Telegram-алерты (пороговые уведомления по цене/спреду)
- ⬜ Шаг 7А — AI-Coach базовый (Claude API)
- ⬜ Шаг 7Б — AI-Аналитик (графики + новости)
- ⬜ Шаг 7В — AI-Предсказатель с самообучением
- ⬜ Шаг 8 — Связки (USDT/USDC, межбиржевые)

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
