"""Бизнес-логика: пользователи, портфели, операции и курсы."""

from datetime import datetime, timezone

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import format_amount, get_pair_rate, parse_amount
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import (
    PORTFOLIOS_FILE,
    RATES_FILE,
    USERS_FILE,
    DatabaseManager,
)
from valutatrade_hub.infra.settings import SettingsLoader

db = DatabaseManager()


def _load_users():
    """Читает список пользователей из хранилища."""
    return db.load(USERS_FILE, [])


def _find_user(username):
    """Ищет пользователя по имени, иначе None."""
    for record in _load_users():
        if record["username"] == username:
            return User.from_dict(record)
    return None


def _load_portfolios():
    """Читает список портфелей."""
    return db.load(PORTFOLIOS_FILE, [])


def _load_portfolio(user_id):
    """Возвращает портфель пользователя или новый пустой."""
    for record in _load_portfolios():
        if record["user_id"] == user_id:
            return Portfolio.from_dict(record)
    return Portfolio(user_id)


def _save_portfolio(portfolio):
    """Сохраняет портфель, добавляя его при первом сохранении."""
    portfolios = _load_portfolios()
    for index, record in enumerate(portfolios):
        if record["user_id"] == portfolio.user_id:
            portfolios[index] = portfolio.to_dict()
            break
    else:
        portfolios.append(portfolio.to_dict())
    db.save(PORTFOLIOS_FILE, portfolios)


def _age_seconds(iso_string):
    """Возвращает возраст записи кэша в секундах."""
    moment = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - moment).total_seconds()


def load_rates():
    """Читает кэш курсов, при устаревании запускает обновление."""
    cache = db.load(RATES_FILE, {})
    pairs = cache.get("pairs", {})
    ttl = SettingsLoader().get("rates_ttl_seconds", 300)
    last_refresh = cache.get("last_refresh")
    if last_refresh is None or _age_seconds(last_refresh) > ttl:
        from valutatrade_hub.parser_service.updater import run_update

        run_update()
        cache = db.load(RATES_FILE, {})
        pairs = cache.get("pairs", {})
    return pairs


def _base_currency():
    """Возвращает базовую валюту из настроек."""
    return SettingsLoader().get("base_currency", "USD")


def _get_fresh_rate(code, base):
    """Получает курс code -> base или бросает ApiRequestError."""
    pairs = load_rates()
    rate = get_pair_rate(pairs, code, base)
    if rate is None:
        raise ApiRequestError(f"нет свежих данных для пары {code}_{base}")
    return rate, pairs


def get_portfolio_summary(username, base=None):
    """Готовит данные портфеля для отображения: кошельки и итог."""
    base = base or _base_currency()
    get_currency(base.upper())
    user = _find_user(username)
    if user is None:
        raise ValueError(f"Пользователь '{username}' не найден")
    portfolio = _load_portfolio(user.user_id)
    rates = load_rates()
    items = []
    for code, wallet in portfolio.wallets.items():
        rate = get_pair_rate(rates, code, base.upper())
        items.append((code, wallet.balance, rate))
    total = portfolio.get_total_value(rates, base.upper())
    return {"base": base.upper(), "items": items, "total": total}


@log_action("REGISTER")
def register(username, password):
    """Создает пользователя с уникальным именем и пустой портфель."""
    users = _load_users()
    if any(record["username"] == username for record in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")
    user_id = 1
    if users:
        user_id = max(record["user_id"] for record in users) + 1
    user = User(user_id, username, password)
    users.append(user.to_dict())
    db.save(USERS_FILE, users)
    portfolio = Portfolio(user_id)
    _save_portfolio(portfolio)
    return {"user_id": user_id, "username": username}


@log_action("LOGIN")
def login(username, password):
    """Проверяет учетные данные и возвращает информацию о пользователе."""
    user = _find_user(username)
    if user is None:
        raise ValueError(f"Пользователь '{username}' не найден")
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")
    return {"user_id": user.user_id, "username": username}


@log_action("BUY", verbose=True)
def buy(username, currency_code, amount):
    """Покупает валюту: автоматически создает кошелек и пополняет баланс."""
    value = parse_amount(amount)
    code = currency_code.upper()
    get_currency(code)
    user = _find_user(username)
    if user is None:
        raise ValueError(f"Пользователь '{username}' не найден")
    rate, _ = _get_fresh_rate(code, _base_currency())
    portfolio = _load_portfolio(user.user_id)
    wallet = portfolio.add_currency(code)
    was = wallet.balance
    wallet.deposit(value)
    _save_portfolio(portfolio)
    return {
        "username": username,
        "currency_code": code,
        "amount": value,
        "rate": rate,
        "base": "USD",
        "was": was,
        "became": wallet.balance,
        "cost": value * rate,
        "was_became": (
            f"{code}: {format_amount(code, was)} -> "
            f"{format_amount(code, wallet.balance)}"
        ),
    }


@log_action("SELL", verbose=True)
def sell(username, currency_code, amount):
    """Продает валюту, проверяя наличие кошелька и средств."""
    value = parse_amount(amount)
    code = currency_code.upper()
    get_currency(code)
    user = _find_user(username)
    if user is None:
        raise ValueError(f"Пользователь '{username}' не найден")
    portfolio = _load_portfolio(user.user_id)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            f"она создаётся автоматически при первой покупке."
        )
    rate, _ = _get_fresh_rate(code, _base_currency())
    was = wallet.balance
    wallet.withdraw(value)
    _save_portfolio(portfolio)
    return {
        "username": username,
        "currency_code": code,
        "amount": value,
        "rate": rate,
        "base": "USD",
        "was": was,
        "became": wallet.balance,
        "revenue": value * rate,
        "was_became": (
            f"{code}: {format_amount(code, was)} -> "
            f"{format_amount(code, wallet.balance)}"
        ),
    }


def get_rate(from_code, to_code):
    """Возвращает курс пары и время обновления кэша."""
    source = get_currency(from_code.upper())
    target = get_currency(to_code.upper())
    pairs = load_rates()
    rate = get_pair_rate(pairs, source.code, target.code)
    if rate is None:
        raise ApiRequestError(
            f"нет свежих данных для пары {source.code}_{target.code}"
        )
    pair = pairs.get(f"{source.code}_USD") or pairs.get(f"{target.code}_USD")
    updated_at = pair["updated_at"] if pair else ""
    return {
        "from": source.code,
        "to": target.code,
        "rate": rate,
        "updated_at": updated_at,
    }
