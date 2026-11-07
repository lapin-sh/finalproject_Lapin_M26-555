"""Командный интерфейс пользователя."""

import shlex

from valutatrade_hub.core import usecases
from valutatrade_hub.core.currencies import CURRENCY_REGISTRY
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.utils import (
    format_amount,
    format_rate,
    format_usd,
)
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.updater import build_updater

PROMPT = "> "
SEPARATOR = "---------------------------------"

HELP_TEXT = """Команды:
  register --username <имя> --password <пароль>
  login --username <имя> --password <пароль>
  show-portfolio [--base USD]
  buy --currency <код> --amount <количество>
  sell --currency <код> --amount <количество>
  get-rate --from <код> --to <код>
  update-rates [--source coingecko|exchangerate]
  show-rates [--currency <код>] [--top N] [--base <код>]
  help
  exit"""


KNOWN_FLAGS = {
    "username", "password", "base", "currency", "amount",
    "from", "to", "source", "top",
}


def parse_flags(tokens):
    """Разбирает аргументы вида --ключ значение в словарь."""
    args = {}
    unknown = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--"):
            key = token[2:]
            if key not in KNOWN_FLAGS:
                unknown.append(token)
            if index + 1 < len(tokens):
                args[key] = tokens[index + 1]
                index += 2
            else:
                args[key] = ""
                index += 1
        else:
            index += 1
    return args, unknown


def _require_login(session):
    """Возвращает имя вошедшего пользователя или печатает ошибку."""
    if session.get("username") is None:
        print("Сначала выполните login")
        return None
    return session["username"]


def handle_register(args):
    """Обрабатывает команду register."""
    username = args.get("username")
    password = args.get("password")
    if not username or password is None:
        print("Использование: register --username <имя> --password <пароль>")
        return
    try:
        result = usecases.register(username=username, password=password)
    except ValueError as error:
        print(error)
        return
    print(
        f"Пользователь '{result['username']}' зарегистрирован "
        f"(id={result['user_id']}). Войдите: login --username "
        f"{result['username']} --password ****"
    )


def handle_login(args, session):
    """Обрабатывает команду login."""
    username = args.get("username")
    password = args.get("password")
    if not username or password is None:
        print("Использование: login --username <имя> --password <пароль>")
        return
    try:
        usecases.login(username=username, password=password)
    except ValueError as error:
        print(error)
        return
    session["username"] = username
    print(f"Вы вошли как '{username}'")


def handle_show_portfolio(args, session):
    """Обрабатывает команду show-portfolio."""
    username = _require_login(session)
    if username is None:
        return
    base = args.get("base")
    try:
        summary = usecases.get_portfolio_summary(username, base)
    except CurrencyNotFoundError:
        print(f"Неизвестная базовая валюта '{(base or '').upper()}'")
        return
    if not summary["items"]:
        print(
            "У вас пока нет кошельков. "
            "Купите валюту: buy --currency BTC --amount 0.01"
        )
        return
    base_code = summary["base"]
    print(f"Портфель пользователя '{username}' (база: {base_code}):")
    for code, balance, rate in summary["items"]:
        if rate is None:
            print(f"- {code}: {format_amount(code, balance)}  → н/д {base_code}")
            continue
        print(
            f"- {code}: {format_amount(code, balance)}  → "
            f"{balance * rate:.2f} {base_code}"
        )
    print(SEPARATOR)
    print(f"ИТОГО: {format_usd(summary['total'])} {base_code}")


def handle_buy(args, session):
    """Обрабатывает команду buy."""
    username = _require_login(session)
    if username is None:
        return
    currency = args.get("currency")
    amount = args.get("amount")
    if not currency or not amount:
        print("Использование: buy --currency <код> --amount <количество>")
        return
    try:
        result = usecases.buy(
            username=username,
            currency_code=currency,
            amount=amount,
        )
    except ValueError as error:
        print(error)
        return
    except CurrencyNotFoundError as error:
        print(error)
        return
    except ApiRequestError:
        print(f"Не удалось получить курс для {currency.upper()}→USD")
        return
    code = result["currency_code"]
    print(
        f"Покупка выполнена: {format_amount(code, result['amount'])} {code} "
        f"по курсу {result['rate']:.2f} USD/{code}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {code}: было {format_amount(code, result['was'])} → "
        f"стало {format_amount(code, result['became'])}"
    )
    print(f"Оценочная стоимость покупки: {format_usd(result['cost'])} USD")


def handle_sell(args, session):
    """Обрабатывает команду sell."""
    username = _require_login(session)
    if username is None:
        return
    currency = args.get("currency")
    amount = args.get("amount")
    if not currency or not amount:
        print("Использование: sell --currency <код> --amount <количество>")
        return
    try:
        result = usecases.sell(
            username=username,
            currency_code=currency,
            amount=amount,
        )
    except ValueError as error:
        print(error)
        return
    except CurrencyNotFoundError as error:
        print(error)
        return
    except InsufficientFundsError as error:
        print(error)
        return
    except ApiRequestError:
        print(f"Не удалось получить курс для {currency.upper()}→USD")
        return
    code = result["currency_code"]
    print(
        f"Продажа выполнена: {format_amount(code, result['amount'])} {code} "
        f"по курсу {result['rate']:.2f} USD/{code}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {code}: было {format_amount(code, result['was'])} → "
        f"стало {format_amount(code, result['became'])}"
    )
    print(f"Оценочная выручка: {format_usd(result['revenue'])} USD")


def handle_get_rate(args):
    """Обрабатывает команду get-rate."""
    source = args.get("from")
    target = args.get("to")
    if not source or not target:
        print("Использование: get-rate --from <код> --to <код>")
        return
    try:
        result = usecases.get_rate(source, target)
    except CurrencyNotFoundError as error:
        print(error)
        print(f"Поддерживаемые коды: {', '.join(CURRENCY_REGISTRY)}")
        return
    except ApiRequestError:
        print(f"Курс {source.upper()}→{target.upper()} недоступен. "
              f"Повторите попытку позже.")
        return
    updated = result["updated_at"].replace("T", " ").replace("Z", "")
    print(
        f"Курс {result['from']}→{result['to']}: {format_rate(result['rate'])} "
        f"(обновлено: {updated})"
    )
    reverse = 1 / result["rate"]
    print(f"Обратный курс {result['to']}→{result['from']}: "
          f"{format_rate(reverse)}")


def handle_update_rates(args):
    """Обрабатывает команду update-rates."""
    source = args.get("source")
    if source not in (None, "coingecko", "exchangerate"):
        print("Источник может быть: coingecko или exchangerate")
        return
    try:
        build_updater(source).run_update()
    except Exception as error:
        print(f"Не удалось обновить курсы: {error}")


def handle_show_rates(args):
    """Обрабатывает команду show-rates."""
    cache = usecases.db.load("rates.json", {})
    pairs = cache.get("pairs", {})
    if not pairs:
        print("Локальный кэш курсов пуст. Выполните 'update-rates', "
              "чтобы загрузить данные.")
        return
    last_refresh = (cache.get("last_refresh") or "").replace("Z", "")
    currency = (args.get("currency") or "").upper()
    base = (args.get("base") or "USD").upper()
    top = None
    if args.get("top"):
        try:
            top = int(args["top"])
        except ValueError:
            print("--top должен быть целым числом")
            return
        if top < 1:
            print("--top должен быть целым числом больше нуля")
            return
    lines = []
    if currency:
        keys = [key for key in pairs if key.startswith(f"{currency}_")]
        if not keys:
            print(f"Курс для '{currency}' не найден в кэше.")
            return
    else:
        keys = list(pairs)
    base_price = pairs.get(f"{base}_USD")
    for key in keys:
        code = key.split("_")[0]
        rate = pairs[key]["rate"]
        if base != "USD" and base_price is not None and code != base:
            rate = rate / base_price["rate"]
            key = f"{code}_{base}"
        lines.append((key, rate))
    lines.sort(key=lambda item: item[1], reverse=True)
    if top:
        lines = lines[:top]
    lines.sort(key=lambda item: item[0])
    print(f"Rates from cache (updated at {last_refresh}):")
    for key, rate in lines:
        print(f"- {key}: {format_rate(rate)}")


def main():
    """Основной цикл интерфейса."""
    setup_logging(SettingsLoader().get("logs_dir", "logs"))
    session = {"username": None}
    print("ValutaTrade Hub. Введите help для списка команд.")
    while True:
        try:
            user_input = input(PROMPT)
        except EOFError:
            break
        try:
            tokens = shlex.split(user_input)
        except ValueError:
            print("Некорректная команда: проверьте кавычки.")
            continue
        if not tokens:
            continue
        command = tokens[0]
        args, unknown = parse_flags(tokens[1:])
        if unknown:
            print(f"Неизвестные аргументы: {' '.join(unknown)}")
        if command == "help":
            print(HELP_TEXT)
        elif command == "exit":
            print("Выход.")
            break
        elif command == "register":
            handle_register(args)
        elif command == "login":
            handle_login(args, session)
        elif command == "show-portfolio":
            handle_show_portfolio(args, session)
        elif command == "buy":
            handle_buy(args, session)
        elif command == "sell":
            handle_sell(args, session)
        elif command == "get-rate":
            handle_get_rate(args)
        elif command == "update-rates":
            handle_update_rates(args)
        elif command == "show-rates":
            handle_show_rates(args)
        else:
            print(f"Неизвестная команда '{command}'. Введите help.")
