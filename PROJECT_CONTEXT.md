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
- scripts/start_tracker.bat — запуск двойным кликом (открывает новое окно PowerShell)
- scripts/start_tracker_background.ps1 — вызывается из .bat, настраивает окружение
- scripts/stop_tracker.ps1 — аварийная остановка по PID
- data/p2p_backup_20260501_morning.db — бэкап первой ночи сбора (3312 снимков, 66394 ордеров)

## На чём остановились

Просмотрщик market.py готов и протестирован. БД содержит тестовые данные (~272 снимка за ~35 мин).

## Следующий шаг — Шаг 1 из плана

План на 5 шагов до первого юзабельного прототипа:
1. Фильтр выбросов (медиана топ-5) + внутрибиржевой спред (BUY-SELL на одной бирже)
2. Risk-метки банков + надёжность мейкеров
3. TUI-дашборд с автообновлением
4. Telegram-алерты
5. AI-агент через Claude API

Сейчас в работе: Шаг 1.

## Workflow обновления документации

После завершения каждого Шага плана обновляются ОБА файла:
- PROJECT_CONTEXT.md — в "Что готово" добавить новые компоненты, в "Следующий шаг" вписать следующий из плана
- CHEATSHEET.md — добавить новые пользовательские команды, убрать устаревшие

## Известные аномалии в данных

В текущем датасете обнаружены систематические ловчие ордера:
- USDT/UAH BUY на Binance: мейкер Quentin777111 держит ордер 42.10 при рыночной цене ~43.50 (объём 10 USDT, 4-й день подряд)
- USDT/UAH BUY на Bybit: fast_retrade ставит 42.00 на объём 3 USDT
- USDC/UAH BUY на Binance: периодически появляются ордера с ценой до 90 UAH

Эти кейсы — основная мотивация для Шага 1 (фильтр выбросов).
