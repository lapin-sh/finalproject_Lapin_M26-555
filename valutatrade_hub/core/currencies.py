"""Иерархия валют и реестр поддерживаемых кодов."""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Базовый класс валюты."""

    def __init__(self, name, code):
        if not name:
            raise ValueError("Имя валюты не может быть пустым")
        code = code.upper()
        if not code.isalnum() or not 2 <= len(code) <= 5:
            raise ValueError(
                "Код валюты: верхний регистр, 2-5 символов, без пробелов"
            )
        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self):
        """Возвращает строковое представление для UI и логов."""


class FiatCurrency(Currency):
    """Фиатная валюта."""

    def __init__(self, name, code, issuing_country):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self):
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(self, name, code, algorithm, market_cap):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self):
        cap = f"{self.market_cap:.2e}".replace("e+", "e")
        return (f"[CRYPTO] {self.code} — {self.name} "
                f"(Algo: {self.algorithm}, MCAP: {cap})")


CURRENCY_REGISTRY = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 3.7e11),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of History", 8.0e10),
}

CRYPTO_CODES = ("BTC", "ETH", "SOL")


def get_currency(code):
    """Возвращает валюту по коду или бросает CurrencyNotFoundError."""
    currency = CURRENCY_REGISTRY.get(code.upper())
    if currency is None:
        raise CurrencyNotFoundError(code)
    return currency
