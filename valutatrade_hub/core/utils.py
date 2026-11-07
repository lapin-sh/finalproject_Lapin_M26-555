"""Вспомогательные функции: валидации, форматирование, конвертации."""

from valutatrade_hub.core.currencies import CRYPTO_CODES

AMOUNT_ERROR = "'amount' должен быть положительным числом"


def format_amount(code, value):
    """Форматирует сумму: у криптовалют 4 знака, у фиата 2."""
    if code in CRYPTO_CODES:
        return f"{value:.4f}"
    return f"{value:.2f}"


# пороги подобраны под примеры ТЗ: 0.00001685, 0.01016, 1.0786, 59337.21
TINY_RATE = 0.001
SMALL_RATE = 0.1
MEDIUM_RATE = 10


def format_rate(value):
    """Форматирует курс: маленькие значения точнее, крупные короче."""
    if value < TINY_RATE:
        return f"{value:.8f}"
    if value < SMALL_RATE:
        return f"{value:.5f}"
    if value < MEDIUM_RATE:
        return f"{value:.4f}"
    return f"{value:.2f}"


def format_usd(value):
    """Форматирует сумму в USD с разделением тысяч."""
    return f"{value:,.2f}"


def parse_amount(value):
    """Преобразует строку в положительное число или бросает ValueError."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError(AMOUNT_ERROR) from None
    if amount <= 0:
        raise ValueError(AMOUNT_ERROR)
    return amount


def get_usd_price(rates_pairs, code):
    """Возвращает цену одной единицы валюты в USD из кэша пар."""
    if code == "USD":
        return 1.0
    pair = rates_pairs.get(f"{code}_USD")
    if pair is None:
        return None
    return pair["rate"]


def get_pair_rate(rates_pairs, from_code, to_code):
    """Считает курс from -> to через USD-цены, None при отсутствии данных."""
    usd_from = get_usd_price(rates_pairs, from_code)
    usd_to = get_usd_price(rates_pairs, to_code)
    if usd_from is None or usd_to is None:
        return None
    return usd_from / usd_to
