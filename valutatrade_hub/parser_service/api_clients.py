"""Клиенты внешних API с единым интерфейсом."""

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig

CONFIG = ParserConfig()


class BaseApiClient(ABC):
    """Базовый клиент: возвращает курсы в формате {"BTC_USD": 59337.21}."""

    source_name = "BaseApiClient"

    @abstractmethod
    def fetch_rates(self):
        """Возвращает словарь пар курса к USD."""


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko: курсы криптовалют."""

    source_name = "CoinGecko"

    def fetch_rates(self):
        """Запрашивает цены криптовалют к USD по их ID."""
        ids = ",".join(CONFIG.CRYPTO_ID_MAP.values())
        try:
            response = requests.get(
                CONFIG.COINGECKO_URL,
                params={"ids": ids, "vs_currencies": "usd"},
                timeout=CONFIG.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as error:
            raise ApiRequestError("Network error") from error
        if response.status_code == 429:
            raise ApiRequestError("превышен лимит запросов CoinGecko (429)")
        if response.status_code != 200:
            raise ApiRequestError(f"CoinGecko вернул HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError as error:
            raise ApiRequestError("некорректный ответ CoinGecko") from error
        id_to_code = {value: key for key, value in CONFIG.CRYPTO_ID_MAP.items()}
        rates = {}
        for coin_id, payload in data.items():
            code = id_to_code.get(coin_id)
            if code is not None and "usd" in payload:
                rates[f"{code}_USD"] = payload["usd"]
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API: курсы фиатных валют."""

    source_name = "ExchangeRate-API"

    def fetch_rates(self):
        """Запрашивает курсы фиатных валют относительно USD."""
        if not CONFIG.EXCHANGERATE_API_KEY:
            raise ApiRequestError("EXCHANGERATE_API_KEY не задан")
        url = (
            f"{CONFIG.EXCHANGERATE_API_URL}/"
            f"{CONFIG.EXCHANGERATE_API_KEY}/latest/{CONFIG.BASE_CURRENCY}"
        )
        try:
            response = requests.get(url, timeout=CONFIG.REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as error:
            raise ApiRequestError("Network error") from error
        if response.status_code == 401:
            raise ApiRequestError("неверный ключ ExchangeRate-API (401)")
        if response.status_code == 429:
            raise ApiRequestError("превышен лимит запросов ExchangeRate-API (429)")
        if response.status_code != 200:
            raise ApiRequestError(
                f"ExchangeRate-API вернул HTTP {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError as error:
            raise ApiRequestError("некорректный ответ ExchangeRate-API") from error
        # у v6 поле называется conversion_rates
        conversions = data.get("conversion_rates", data.get("rates", {}))
        rates = {}
        for code in CONFIG.FIAT_CURRENCIES:
            price = conversions.get(code)
            if price:
                # API отдает единиц валюты за 1 USD, нам нужен курс к USD
                rates[f"{code}_USD"] = 1 / price
        return rates
