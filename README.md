# p2p-system

Мониторинг P2P курсов USDT/USDC к UAH на Binance и Bybit.

## Структура папок

```
p2p-system/
├── config/             # Настройки и переменные окружения
├── core/
│   ├── database/       # Модели и сессии SQLAlchemy
│   ├── exchanges/      # Клиенты Binance и Bybit P2P API
│   └── utils/          # Логгер и вспомогательные утилиты
├── modules/
│   └── tracker/        # Планировщик сбора и сохранения данных
├── data/               # SQLite база данных
├── logs/               # Лог-файлы
├── main.py
└── requirements.txt
```

## Как запустить

```bash
# Активация виртуального окружения
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# Установка зависимостей
pip install -r requirements.txt

# Копирование конфига
copy config\.env.example config\.env   # Windows
# cp config/.env.example config/.env  # Linux/macOS

# Запуск
python main.py
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/p2p.db` | URL базы данных |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `TRACKER_INTERVAL_SECONDS` | `60` | Интервал обычного сбора (сек) |
| `DEEP_SNAPSHOT_INTERVAL_SECONDS` | `900` | Интервал глубокого снимка (сек) |
