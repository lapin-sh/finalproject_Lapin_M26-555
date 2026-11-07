"""Модели: User, Wallet, Portfolio."""

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.utils import format_amount

PASSWORD_MIN_LENGTH = 4


def hash_password(password, salt):
    """Односторонний псевдо-хеш пароля с солью."""
    return hashlib.sha256((password + salt).encode()).hexdigest()


class User:
    """Пользователь системы."""

    def __init__(self, user_id, username, password, registration_date=None):
        self._user_id = user_id
        self.username = username
        if len(password) < PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"Пароль должен быть не короче {PASSWORD_MIN_LENGTH} символов"
            )
        self._salt = secrets.token_hex(4)
        self._hashed_password = hash_password(password, self._salt)
        if registration_date is None:
            registration_date = datetime.now()
        self._registration_date = registration_date

    @property
    def user_id(self):
        return self._user_id

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        if not value:
            raise ValueError("Имя пользователя не может быть пустым")
        if " " in value:
            raise ValueError("Имя пользователя не должно содержать пробелов")
        self._username = value

    @property
    def registration_date(self):
        return self._registration_date

    def get_user_info(self):
        """Возвращает информацию о пользователе без пароля."""
        return (
            f"Пользователь #{self._user_id}: {self._username} "
            f"(зарегистрирован {self._registration_date:%Y-%m-%d %H:%M})"
        )

    def change_password(self, new_password):
        """Меняет пароль: новая соль и новый хеш."""
        if len(new_password) < PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"Пароль должен быть не короче {PASSWORD_MIN_LENGTH} символов"
            )
        self._salt = secrets.token_hex(4)
        self._hashed_password = hash_password(new_password, self._salt)

    def verify_password(self, password):
        """Проверяет введенный пароль."""
        return hash_password(password, self._salt) == self._hashed_password

    def to_dict(self):
        """Сериализует пользователя для users.json."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data):
        """Создает пользователя из записи users.json."""
        user = cls.__new__(cls)
        user._user_id = data["user_id"]
        user._username = data["username"]
        user._salt = data["salt"]
        user._hashed_password = data["hashed_password"]
        user._registration_date = datetime.fromisoformat(
            data["registration_date"]
        )
        return user


class Wallet:
    """Кошелек пользователя для одной валюты."""

    def __init__(self, currency_code, balance=0.0):
        self.currency_code = currency_code
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount):
        """Пополняет баланс."""
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        self.balance += amount

    def withdraw(self, amount):
        """Списывает средства, проверяя остаток."""
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        if amount > self._balance:
            available = format_amount(self.currency_code, self._balance)
            required = format_amount(self.currency_code, amount)
            raise InsufficientFundsError(available, required, self.currency_code)
        self.balance -= amount

    def get_balance_info(self):
        """Возвращает информацию о балансе."""
        amount = format_amount(self.currency_code, self._balance)
        return f"Кошелек {self.currency_code}: {amount}"

    def to_dict(self):
        """Сериализует кошелек для portfolios.json."""
        return {
            "currency_code": self.currency_code,
            "balance": round(self._balance, 8),
        }

    @classmethod
    def from_dict(cls, data):
        """Создает кошелек из записи portfolios.json."""
        return cls(data["currency_code"], data.get("balance", 0.0))


class Portfolio:
    """Портфель: все кошельки одного пользователя."""

    def __init__(self, user_id, wallets=None):
        self._user_id = user_id
        self._wallets = wallets if wallets is not None else {}

    @property
    def user_id(self):
        """Только геттер: перезаписывать владельца портфеля нельзя."""
        return self._user_id

    @property
    def wallets(self):
        """Возвращает копию словаря кошельков."""
        return dict(self._wallets)

    def add_currency(self, currency_code):
        """Добавляет кошелек, если его еще нет. Возвращает кошелек."""
        if currency_code not in self._wallets:
            self._wallets[currency_code] = Wallet(currency_code)
        return self._wallets[currency_code]

    def get_wallet(self, currency_code):
        """Возвращает кошелек по коду валюты или None."""
        return self._wallets.get(currency_code)

    def get_total_value(self, rates_pairs, base_currency="USD"):
        """Считает общую стоимость портфеля в базовой валюте."""
        total = 0.0
        for code, wallet in self._wallets.items():
            if code == base_currency:
                total += wallet.balance
                continue
            usd_price = rates_pairs.get(f"{code}_USD")
            base_price = rates_pairs.get(f"{base_currency}_USD")
            if base_currency == "USD":
                if usd_price is None:
                    continue
                total += wallet.balance * usd_price["rate"]
            elif usd_price is not None and base_price is not None:
                rate = usd_price["rate"] / base_price["rate"]
                total += wallet.balance * rate
        return total

    def to_dict(self):
        """Сериализует портфель для portfolios.json."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: wallet.to_dict()
                for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data):
        """Создает портфель из записи portfolios.json."""
        wallets = {}
        for code, wallet_data in data.get("wallets", {}).items():
            wallets[code] = Wallet.from_dict(wallet_data)
        return cls(data["user_id"], wallets)
