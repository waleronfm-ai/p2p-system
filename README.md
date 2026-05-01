# P2P System

Система мониторинга P2P курсов криптовалют на биржах Binance и Bybit.

## Что делает

- Каждую минуту собирает топ-20 ордеров с обеих бирж по парам USDT/UAH и USDC/UAH
- Каждые 15 минут — глубокий снимок (топ-100)
- Хранит историю в SQLite базе данных
- Предоставляет аналитику: динамику курса, спред между биржами, статистику мейкеров

## Технический стек

- Python 3.13
- SQLAlchemy 2.0 — работа с БД
- httpx — HTTP-клиент для API бирж
- APScheduler — планировщик сбора
- pydantic-settings — конфигурация
- rich — красивый вывод в терминале

## Структура проекта

p2p-system/
├── core/               # общая инфраструктура
│   ├── database/       # модели БД и сессии
│   ├── exchanges/      # клиенты Binance и Bybit
│   └── utils/          # логгер, часовые пояса
├── modules/
│   └── tracker/        # сборщик данных
├── scripts/            # точки входа (init_db, run_tracker, market, ...)
├── config/             # настройки
├── data/               # SQLite БД (не в репозитории)
└── logs/               # логи (не в репозитории)

## Запуск

```powershell
# Активация виртуального окружения
.\venv\Scripts\Activate.ps1

# Инициализация БД (один раз)
python scripts/init_db.py

# Запуск трекера
.\scripts\start_tracker.bat

# Просмотр данных
python scripts/market.py summary
python scripts/market.py chart USDT/UAH --hours 1
python scripts/market.py spread USDT/UAH --hours 6
```

## Часовые пояса

В БД всё хранится в UTC. Отображение и логи — в Europe/Kyiv.