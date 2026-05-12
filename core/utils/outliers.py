"""Фильтрация выбросов в P2P-ордерах."""

import statistics


def _get_price(order) -> float:
    """Достаёт цену из объекта или словаря."""
    if isinstance(order, dict):
        return float(order["price"])
    return float(order.price)


def median_price(orders: list) -> float:
    """Медиана цен из списка ордеров.

    Принимает список объектов с полем .price или словарей с ключом "price".

    Args:
        orders: список ордеров (SQLAlchemy Order или dict)

    Returns:
        медиана цен; 0.0 если список пустой

    Пример:
        >>> from types import SimpleNamespace
        >>> orders = [SimpleNamespace(price=43.5), SimpleNamespace(price=42.1), SimpleNamespace(price=43.6)]
        >>> median_price(orders)
        43.5
    """
    if not orders:
        return 0.0
    prices = [_get_price(o) for o in orders]
    return statistics.median(prices)


def is_outlier(price: float, median: float, side: str, threshold: float = 0.10) -> bool:
    """Проверяет, является ли цена выбросом относительно медианы.

    Args:
        price: проверяемая цена
        median: медиана по выборке
        side: "BUY" или "SELL"
        threshold: допустимое отклонение (0.10 = 10%)

    Returns:
        True если цена — выброс

    Логика:
        BUY:  выброс = цена слишком низкая → ловушка для покупателя
        SELL: выброс = цена слишком высокая → ловушка для продавца

    Пример:
        >>> is_outlier(42.1, 43.5, "BUY")   # 3.2% ниже медианы — НЕ выброс
        False
        >>> is_outlier(40.0, 43.5, "BUY")   # 8.0% ниже медианы — НЕ выброс
        False
        >>> is_outlier(39.0, 43.5, "BUY")   # 10.3% ниже медианы — выброс
        True
        >>> is_outlier(90.0, 44.0, "SELL")  # 104% выше медианы — выброс
        True
    """
    if median == 0.0:
        return False
    if side == "BUY":
        return price < median * (1 - threshold)
    if side == "SELL":
        return price > median * (1 + threshold)
    return False


def filter_outliers(
    orders: list,
    side: str,
    top_n: int = 5,
    threshold: float = 0.10,
) -> tuple[list, list]:
    """Разделяет ордера на чистые и выбросы.

    Берёт первые top_n ордеров (они отсортированы биржей по выгодности),
    считает медиану по ним, затем проверяет каждый из top_n.

    Args:
        orders: список всех ордеров из снимка
        side: "BUY" или "SELL"
        top_n: сколько топовых ордеров брать для анализа
        threshold: порог отклонения (0.05 = 5%)

    Returns:
        (clean_orders, outlier_orders) — оба списка из top_n ордеров

    Пример:
        >>> from types import SimpleNamespace
        >>> orders = [SimpleNamespace(price=p) for p in [42.1, 43.5, 43.6, 43.7, 43.8]]
        >>> clean, bad = filter_outliers(orders, "BUY")
        >>> len(bad)
        0
        >>> len(clean)
        5
    """
    if not orders:
        return [], []

    sample = orders[:top_n]
    med = median_price(sample)

    clean: list = []
    outliers: list = []
    for order in sample:
        price = _get_price(order)
        if is_outlier(price, med, side, threshold):
            outliers.append(order)
        else:
            clean.append(order)

    return clean, outliers


def get_clean_top1(
    orders: list,
    side: str,
    threshold: float = 0.10,
) -> object | None:
    """Возвращает первый чистый ордер из топ-5.

    Args:
        orders: список ордеров из снимка (отсортированных биржей)
        side: "BUY" или "SELL"
        threshold: порог отклонения

    Returns:
        первый ордер без признаков выброса, или None если все top_5 — выбросы

    Пример:
        >>> from types import SimpleNamespace
        >>> orders = [SimpleNamespace(price=42.1), SimpleNamespace(price=43.5)]
        >>> result = get_clean_top1(orders, "BUY")
        >>> result.price
        42.1
    """
    clean, _ = filter_outliers(orders, side, top_n=5, threshold=threshold)
    return clean[0] if clean else None
