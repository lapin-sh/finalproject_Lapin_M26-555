"""Доменные исключения приложения."""


class InsufficientFundsError(Exception):
    """Недостаточно средств на кошельке."""

    def __init__(self, available, required, code):
        super().__init__(
            f"Недостаточно средств: доступно {available} {code}, "
            f"требуется {required} {code}"
        )


class CurrencyNotFoundError(Exception):
    """Неизвестный код валюты."""

    def __init__(self, code):
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Сбой при обращении к внешнему API."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
