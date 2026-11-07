"""Декоратор логирования доменных операций."""

import functools
import logging

from valutatrade_hub.core.utils import format_amount

actions_log = logging.getLogger("actions")


def log_action(action, verbose=False):
    """Логирует операцию и ее результат, исключения пробрасывает дальше.

    При verbose=True добавляет контекст изменения кошелька (было -> стало).
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            username = kwargs.get("username", "-")
            currency = kwargs.get("currency_code", "-")
            amount = kwargs.get("amount", "-")
            if currency != "-" and amount != "-":
                try:
                    amount = format_amount(currency, float(amount))
                except (TypeError, ValueError):
                    pass
            try:
                result = func(*args, **kwargs)
                rate = "-"
                base = "-"
                extra = ""
                if isinstance(result, dict):
                    rate = result.get("rate", "-")
                    if isinstance(rate, float):
                        rate = f"{rate:.2f}"
                    base = result.get("base", "-")
                    if verbose and result.get("was_became"):
                        extra = " " + result["was_became"]
                actions_log.info(
                    "%s user='%s' currency='%s' amount=%s rate=%s base='%s' "
                    "result=OK%s",
                    action, username, currency, amount, rate, base, extra,
                )
                return result
            except Exception as error:
                actions_log.error(
                    "%s user='%s' currency='%s' amount=%s result=ERROR "
                    "error=%s",
                    action, username, currency, amount, error,
                )
                raise

        return wrapper

    return decorator
