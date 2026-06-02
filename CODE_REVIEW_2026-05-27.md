# Code Review для переноса в облако (2026-05-27)

> **Статус на 2 июня 2026:**
> Все блокеры Priority 1 закрыты до деплоя на VPS (30 мая 2026).
> Закрыто: X-Api-Key защита write-эндпоинтов, retry с дифференциацией HTTP-ошибок,
> CORS через переменные окружения, индексы БД, расчёт P&L, `requirements_lock.txt`, systemd unit-файлы.
> Оставшиеся пункты (Priority 2/3) — косметика, не блокеры, актуальны для будущих сессий.

## Сводка

Кодовая база в хорошем состоянии для pet-проекта: читаемый Python 3.13, SQLAlchemy 2.0 без устаревших паттернов, грамотная структура модулей. Из реальных блокеров переноса — только два: хардкод Windows-пути в `.ps1`-скрипте и отсутствие защиты write-эндпоинтов. Всё остальное — шероховатости, которые стоит поправить до AI-агента или при переезде.

---

## КРИТИЧНО (Priority 1) — блокеры переноса

### Захардкоженные пути

**`scripts/start_tracker_background.ps1:2-5`** — абсолютный путь к пользователю Windows:
```powershell
Set-Location "C:\Users\inkvi\p2p-system"
$env:PYTHONPATH = "C:\Users\inkvi\p2p-system"
```
На VPS это вызовет немедленный сбой. Как фиксить: заменить на `$PSScriptRoot/..` (для `.ps1`) или вообще перейти на `systemd` unit + рабочую директорию. Скрипт на Linux всё равно не нужен — он Windows-специфичен.

**`scripts/run_tracker.py:3`** — ручной `sys.path.insert` для корня:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```
Это работает, но хрупко. На VPS лучше запускать через `python -m scripts.run_tracker` из корня с правильно настроенным `PYTHONPATH`. Как фиксить: добавить `PYTHONPATH=/opt/p2p-system` в systemd unit, тогда `sys.path.insert` станет ненужным.

### print() вместо логгера

В `scripts/clear_db.py:15,23,29` используется голый `print()` вместо логгера — на VPS вывод в stdout теряется при запуске через systemd без `--no-redirect`. Не критично для clear_db (утилита запускается вручную), но стоит учитывать.

### Обработка ошибок Binance API (retry при 500/таймаут/нет сети)

**`core/exchanges/binance.py:76-88`** — retry через `_with_retry` (в `collector.py`) работает для любых исключений, включая `httpx.HTTPError`. Но проблема: в `_fetch_page` при `response.raise_for_status()` поднимается исключение **с деталями HTTP-кода**, а в `_with_retry` (collector.py:47-61) поглощаются **все** исключения без разбора. Нет дифференциации: 429 (rate limit — нужна пауза подольше) vs 500 (серверная ошибка — можно сразу retry) vs сетевой таймаут.

На VPS это важнее: нет домашнего интернета с буферизацией, есть реальные промежуточные обрывы. Как фиксить: в `_with_retry` проверять тип исключения и для 429 добавлять увеличенный delay.

**`core/exchanges/bybit.py:66`** — Bybit не поддерживает пагинацию (`page` зафиксирован на `"1"`, rows передаётся как `size`). При `rows=100` Bybit может вернуть меньше — нет проверки числа реально вернувшихся элементов vs запрошенных (в отличие от Binance где есть `break` при нехватке).

### Блокирующие операции в async-контексте

**`api/routers/trades.py`, `api/routers/market.py`, все роутеры** — FastAPI запускается через uvicorn, но все обработчики синхронные (`def`, не `async def`). SQLAlchemy используется синхронный. Это **нормально** для текущего объёма. Uvicorn запускает синхронные хендлеры в threadpool. Проблема возникнет только при высокой нагрузке. На VPS с одним пользователем — не блокер.

Единственный `async def lifespan` в `api/main.py:11` — пустой (только `yield`), корректен.

### Write-эндпоинты без защиты

Все write-операции открыты без авторизации. Любой, кто получит доступ к API (даже через Cloudflare Tunnel), сможет создавать и удалять сделки:

| Метод | Путь | Файл:строка |
|-------|------|-------------|
| POST | /api/trades | `api/routers/trades.py:14` |
| DELETE | /api/trades/{trade_id} | `api/routers/trades.py:108` |

Как фиксить: добавить FastAPI dependency с проверкой `X-API-Key` header. Пример:
```python
from fastapi import Depends, Header, HTTPException

def require_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(403)

@router.post("", dependencies=[Depends(require_api_key)])
```

### SQL injection (f-string с user input в SQL)

Прямых SQL injection нет: весь код использует SQLAlchemy ORM с параметрами (`.where(Model.field == value)`). Единственный `text("SELECT 1")` в `health.py:17` — статическая строка, безопасен. Находок нет.

### CORS (что сейчас, что менять для прода)

**`api/main.py:23-28`** — текущий CORS:
```python
allow_origins=["http://localhost:5173", "http://localhost:3000"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
```

Для переноса: фронтенд остаётся локально (`localhost:5173`), API переезжает на VPS за Cloudflare Tunnel. Нужно добавить URL туннеля в `allow_origins`. Если доступ к API только с вашего IP — можно также добавить IP-фильтр на уровне Cloudflare. Как фиксить: вынести `CORS_ORIGINS` в `.env`, читать через `settings`.

### Логирование секретов

`.env` не содержит секретных ключей (только DATABASE_URL, LOG_LEVEL, интервалы). В логах нигде не пишется содержимое запросов/ответов бирж целиком — только статус и количество ордеров. Находок нет.

---

## ВАЖНО (Priority 2) — поправить до AI-агента

### Индексы в БД

**`core/database/models.py:12-60`** — у таблиц `makers`, `snapshots`, `orders` практически нет индексов:

- `Snapshot`: нет индекса на `(exchange, asset, fiat, trade_type)` + `collected_at` — это самый частый фильтр во всех запросах. Сейчас sqlite делает full-scan по сотням тысяч строк.
- `Snapshot`: нет индекса на `collected_at` отдельно — нужен для `ORDER BY collected_at DESC LIMIT 1`.
- `Order`: нет индекса на `snapshot_id` — ForeignKey не создаёт индекс автоматически в SQLAlchemy. `WHERE snapshot_id IN (...)` без индекса = медленно на 1M+ строк.
- `Maker`: нет индекса на `exchange` — UniqueConstraint по `(exchange, external_id)` создаёт индекс неявно, это покрывает lookup. Нормально.
- `Trade`: есть `ix_trades_executed_at` и уникальный `ix_trades_order_id` — хорошо.

Как фиксить (в `models.py`):
```python
# Snapshot
__table_args__ = (
    Index("ix_snap_combo", "exchange", "asset", "fiat", "trade_type", "collected_at"),
    Index("ix_snap_collected_at", "collected_at"),
)
# Order
__table_args__ = (
    Index("ix_order_snapshot_id", "snapshot_id"),
)
```

### N+1 в SQL-запросах

**`api/services/market_service.py:149-196`** — функция `get_summary()` делает N+2 запросов на каждую комбинацию exchange/asset/fiat/trade_type: один для `order_count`, ещё один для `min_p/max_p` (при `raw=True`). При 8 парах (2 биржи × 2 asset × 2 trade_type) = 8 × 3 = 24 запроса за один вызов. Для SQLite некритично, но при переезде на PostgreSQL это станет заметно.

**`api/services/market_service.py:94-119`** — `_clean_series()` делает 2 запроса: один для snapshot IDs, второй для всех orders. Нормально.

**`api/services/market_service.py:337-357`** — `get_outliers()`: для каждой из 8 комбинаций делается отдельный запрос за snaps, потом один большой `IN(...)` за orders. Приемлемо.

### Производительность на 7D/30D таймфреймах

**`api/services/market_service.py:95-119`** — при `hours=168` (7 дней) `_clean_series()` загружает в память **все** orders за 7 дней для пары. При базовом интервале 60 секунд + 8 пар = ~10 000 снапшотов × 20 ордеров = 200 000 строк за один вызов `get_chart()`. Уже сейчас при 51 MB БД это может занимать секунды.

**`api/services/market_service.py:431-435`** — `get_chart()` тоже делает `Order.snapshot_id.in_(snap_ids)` где `snap_ids` может быть списком из 10 000 элементов. SQLite имеет лимит на `IN(...)` в 999 элементов по умолчанию! При hours=168 это потенциальный runtime error.

Как фиксить: разбить `snap_ids` на чанки по 900 и делать несколько запросов, либо использовать JOIN вместо IN.

### Размер БД через год

Текущий размер: **51 MB** (судя по файлу p2p.db). Темп роста:
- Базовые снимки: 8 пар × 20 ордеров × ~14 записей/час × 24 × 365 ≈ 10M ордеров/год
- Глубокие снимки: 8 пар × 100 ордеров × ~24 раза/день × 365 ≈ 2.6M ордеров/год

Итого ~12M строк в `orders` в год. SQLite справится, но запросы замедлятся без индексов (см. выше). Нужна стратегия: либо партиционирование по времени (удалять данные старше N месяцев), либо агрегация (хранить только top-1 по часу, а не все ордера).

### Баг profit_uah в TradeStats (формула при несбалансированных BUY/SELL)

**`api/routers/trades.py:95`**:
```python
pnl_uah=round(total_uah_received - total_uah_spent, 2),
```

Это формула **реализованного** P&L, но она некорректна когда BUY > SELL (есть открытая позиция): если купили 1000 USDT за 43 000 UAH и продали 500 USDT за 22 000 UAH, то `pnl_uah = 22000 - 43000 = -21000` — это не P&L, это просто разность трат/поступлений. Настоящий P&L от продаж = `22000 - 500 * avg_buy_price`.

**`api/routers/position.py:30`** считает это правильно:
```python
realized_profit_uah = round(total_sell_uah - total_sell_usdt * avg_buy_price, 4)
```

То есть TradeStats.pnl_uah врёт при несбалансированной позиции. Как фиксить: переиспользовать формулу из `position.py`.

### Баг залипающего тултипа opportunity в PriceChart.tsx

**`frontend/src/components/PriceChart.tsx:191-195`** — тултип `OppTooltip` отображается через state `hoveredOpp`, который сбрасывается в `null` по `onMouseLeave` на SVG `<circle>`. Проблема: если курсор быстро выходит за границу круга и попадает на другой элемент (например, на BandLayer или на другой `<circle>`), `onMouseLeave` на первом круге может не сработать (React synthetic events на SVG иногда глючат при быстром движении между перекрывающимися элементами). Тултип залипает до следующего движения мыши. Решение: вешать глобальный `onMouseMove` на контейнер (`div` с `onMouseMove` уже есть на строке 685) и добавить туда же `onMouseLeave={() => setHoveredOpp(null)}`, чтобы сброс происходил при уходе мыши за пределы всего chart-контейнера, а не только конкретного круга.

### Дубликаты, мёртвые функции, неиспользуемые импорты

- **`api/routers/trades.py:6`** — `func` из sqlalchemy импортируется, но нигде не используется в файле.
- **`api/services/market_service.py:14-19`** — импортируется `get_worst_risk` из `core.banks.registry`, но в `market_service.py` он нигде не вызывается. Используется только `classify_payment_methods`, `find_bank`, `methods_match_bank`, `RiskLevel`.
- **`core/exchanges/binance.py:135-175`** и **`core/exchanges/bybit.py:123-164`** — блоки `if __name__ == "__main__"` — debug-скрипты внутри production-модулей. Не вредят, но засоряют файлы. На VPS при случайном запуске файла напрямую выполнят HTTP-запросы к бирже.
- **`_load_position()`** в `market_service.py:483-494` и аналогичная логика в `position.py:14-34` — дублирование расчёта позиции в двух местах. При изменении формулы нужно менять в двух файлах.
- **`api/routers/info.py:33`** — `latest_snapshot.astimezone()` без явного указания timezone использует системную TZ. На VPS с UTC как системной это нормально, но лучше `to_kyiv(latest_snapshot).isoformat()` для консистентности.

---

## ПОЖЕЛАТЕЛЬНО (Priority 3)

### requirements.txt (версии, чего не хватает)

**`requirements.txt`** — версии указаны только через `>=`, без верхней границы. На VPS при первой установке поставятся самые свежие версии, что иногда ломает совместимость (особенно major-версии recharts, fastapi). Как фиксить: зафиксировать через `pip freeze > requirements_lock.txt` и использовать его для VPS-установки.

Чего не хватает в `requirements.txt`:
- `python-multipart` — нужен FastAPI для form data (если когда-нибудь понадобится)
- Нет явного `anyio`, `starlette` — зависимости fastapi, обычно тянутся транзитивно, но лучше зафиксировать

### .env.example

Файл `config/.env` содержит реальные значения (DATABASE_URL и параметры без секретов). Нет `.env.example` как шаблона. На VPS придётся вспоминать какие переменные нужны. Как фиксить: создать `config/.env.example` с пустыми/placeholder значениями и закоммитить. Текущий `.env` в `.gitignore` проверить не успел, но он в репо виден.

Проверить: **убедиться что `config/.env` не закоммичен в git** (там нет секретов, но практика хорошая).

### .bat/.ps1 → Linux-эквиваленты

Для VPS все `.bat` и `.ps1` файлы не нужны. Нужны:
- `systemd` unit-файл для трекера (постоянный запуск, автоперезапуск)
- `systemd` unit-файл для uvicorn API
- Или `docker-compose.yml` (см. ниже)

Скрипты для VPS:
```
scripts/
  start_tracker.sh    # запуск трекера в screen/tmux или через systemd
  start_api.sh        # запуск uvicorn
```

### Готовность к Docker

Проект структурирован хорошо для Docker-изации, но:
- `database_url = "sqlite:///data/p2p.db"` — относительный путь, нужен volume mount `/app/data`
- `logs/` тоже нужен как volume
- Нет `Dockerfile` и `docker-compose.yml`
- `__main__` блоки в exchange-клиентах (упомянуто выше) создадут путаницу при `CMD python -m core.exchanges.binance`

---

## Архитектурные мысли

`_load_position()` в `market_service.py` дублирует логику из `position.py` — при добавлении фильтров (например, по паре) нужно менять в двух местах. Стоит вынести в отдельный сервис `PositionService` или хотя бы в `core/`.

Константы opportunities (`_TARGET_PROFIT_PER_USDT = 0.3`, `_ENTRY_DISCOUNT_PERCENT = 0.3`, `_ONLY_SAFE_BANKS = True`) захардкожены в `market_service.py:39-42` — при переезде и добавлении нескольких пользователей (или просто при тюнинге) удобнее иметь их в settings или передавать параметрами.

Bybit удаляется — это упростит код коллектора и уберёт весь маппинг payment ID → bank name из `registry.py`. После удаления `_SIDE_MAP` и Bybit-specific `is_merchant`-поле логика станет чище.

`BlockingScheduler` из APScheduler — правильный выбор для синхронного кода, но на VPS при падении процесса нет автоперезапуска. Нужен systemd с `Restart=always`.

---

## Список Bybit-связанных файлов и кода для удаления

| Файл | Что удалить |
|------|-------------|
| `core/exchanges/bybit.py` | Весь файл (BybitP2PClient, BybitP2POrder, `_SIDE_MAP`, `__main__`) |
| `modules/tracker/collector.py:13` | `from core.exchanges.bybit import BybitP2PClient, BybitP2POrder` |
| `modules/tracker/collector.py:21` | `AnyOrder = Union[BinanceP2POrder, BybitP2POrder]` → просто `BinanceP2POrder` |
| `modules/tracker/collector.py:88-93` | Блок `else: with BybitP2PClient() as client:` |
| `modules/tracker/collector.py:209` | `for exchange in ["binance", "bybit"]:` → `for exchange in ["binance"]:` (или убрать цикл) |
| `api/routers/market.py:58,74` | Валидация `exchange must be 'binance' or 'bybit'` → `'binance'` only |
| `api/routers/trades.py:19` | Валидация `exchange must be 'binance' or 'bybit'` |
| `api/main.py:19` | `description` — убрать упоминание Bybit |
| `api/routers/info.py:25` | `"exchanges": ["Binance", "Bybit"]` → `["Binance"]` |
| `core/banks/registry.py:204-211` | `_BYBIT_ID_INDEX` и весь bybit-specific код (`_resolve` ветка `if m.isdigit()`, `_GENERIC_BYBIT`) |
| `core/banks/registry.py:27-200` | Поля `bybit_ids` во всех записях реестра |
| `scripts/market.py` | Фильтры `--exchange bybit`, упоминания Bybit в help-тексте |
| `PROJECT_CONTEXT.md` | Упоминания Bybit в описании пар |
| `scripts/start_tracker_background.ps1` | Не нужен на Linux |
| `scripts/start_tracker.bat`, `scripts/run_api.bat`, `start_all.bat`, `scripts/3_MARKET.bat` | Не нужны на Linux |

---

## Список write-эндпоинтов для защиты API-key

| Метод | Путь | Файл:строка | Приоритет защиты |
|-------|------|-------------|-----------------|
| POST | /api/trades | `api/routers/trades.py:14` | ВЫСОКИЙ — создаёт записи в БД |
| DELETE | /api/trades/{trade_id} | `api/routers/trades.py:108` | ВЫСОКИЙ — удаляет данные |

Все остальные эндпоинты — только GET, то есть read-only. При наличии Cloudflare Tunnel с access control (IP allowlist или One-Time PIN) этого может быть достаточно как первого слоя. API-key middleware — второй слой.

---

**Итог:** Priority 1: 4 реальных пункта (хардкод пути, retry без дифференциации по кодам, открытые write-эндпоинты, CORS без VPS origin). Priority 2: 7 пунктов (индексы, IN() лимит SQLite, pnl_uah баг, залипающий тултип, дубли логики позиции, неиспользуемые импорты, масштаб БД). Priority 3: 4 пункта (requirements lock, .env.example, Linux-скрипты, Docker).

**Топ-3 самые важные находки:**
1. **`api/routers/trades.py:14,108`** — POST /api/trades и DELETE без авторизации — на VPS это должно быть первым, что фиксится.
2. **`core/database/models.py`** — нет индексов на `snapshots(exchange, asset, fiat, trade_type, collected_at)` и `orders(snapshot_id)` — при текущем росте данных запросы chart/summary через 2-3 месяца станут заметно медленнее.
3. **`api/services/market_service.py:431`** — `Order.snapshot_id.in_(snap_ids)` с потенциально 10 000+ элементами при hours=168 — это SQLite runtime error (лимит 999 элементов в IN по умолчанию) на 7D-таймфрейме.
