# Шпаргалка P2P-System
Шпаргалка по запуску и использованию системы. Обновляется по мере добавления функций.

## Старт сессии
Открыть PowerShell в папке проекта и выполнить:
```
cd C:\Users\inkvi\p2p-system
.\venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"
```
В начале строки должно появиться `(venv)` — окружение активировать

```
git push                  — отправить на GitHub
git log --oneline         — история
git checkout file.py      — откатить файл
git reset --hard HEAD     — отменить ВСЁ несохранённое (осторожно!)
```
Адрес репозитория: https://github.com/waleronfm-ai/p2p-system

## Claude Code
```
claude        — запуск
/effort max   — режим глубоких размышлений
/cost         — расход токенов
/status       — статус сессии
/compact      — сжать историю
/exit         — выход
```

## Типовые ошибки
```
ModuleNotFoundError: No module named ...  → Активировать venv: .\venv\Scripts\Activate.ps1
Кракозябры вместо кириллицы             → Включить UTF-8: $env:PYTHONUTF8 = "1"
Окно трекера не реагирует на Ctrl+C     → .\scripts\stop_tracker.ps1
git: not a git repository               → Не в папке проекта: cd C:\Users\inkvi\p2p-system
git push запрашивает пароль             → Авторизация слетела, должно открыться окно браузера для входа
```

## Просмотрщик market.py

По умолчанию команды используют чистые цены (фильтр выбросов). Флаг --raw возвращает сырые данные (для диагностики).

```
python scripts/market.py summary [--hours N] [--raw]
python scripts/market.py chart USDT/UAH [--hours N] [--side BUY/SELL/BOTH] [--raw]
python scripts/market.py spread USDT/UAH [--hours N] [--raw]
python scripts/market.py makers USDT/UAH [--side BUY/SELL] [--top N] [--exchange binance/bybit/both]
python scripts/market.py latest [--raw]
python scripts/market.py outliers [--hours N] [--pair USDT/UAH] [--side BUY/SELL]
python scripts/market.py find USDT/UAH --side BUY [--bank NAME] [--avoid-banks N1,N2] [--min-orders N] [--min-completion N] [--exchange E] [--top N] [--raw]
```

Примеры полезных запросов find:
```
# Безопасные ордера на ПриватБанке:
python scripts/market.py find USDT/UAH --side BUY --bank Privat --min-orders 500

# Избегать Ощадбанк:
python scripts/market.py find USDT/UAH --side SELL --avoid-banks Oschad
```

## Полезные пути
```
Проект: C:\Users\inkvi\p2p-system
БД:     data\p2p.db
Логи:   logs\
Бэкапы: data\p2p_backup_*.db
```
