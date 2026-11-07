"""Загрузка конфигурации приложения (паттерн Singleton)."""

import tomllib
from pathlib import Path

DEFAULT_SETTINGS = {
    "data_dir": "data",
    "logs_dir": "logs",
    "rates_ttl_seconds": 300,
    "base_currency": "USD",
}


class SettingsLoader:
    """Единая точка доступа к настройкам проекта.

    Singleton реализован через __new__: это проще метакласса и достаточен,
    чтобы при любом количестве импортов существовал один экземпляр.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._settings = dict(DEFAULT_SETTINGS)
            instance._load_pyproject()
            cls._instance = instance
        return cls._instance

    def _load_pyproject(self):
        """Читает секцию [tool.valutatrade] из pyproject.toml."""
        path = Path("pyproject.toml")
        if not path.exists():
            return
        with open(path, "rb") as file:
            data = tomllib.load(file)
        section = data.get("tool", {}).get("valutatrade", {})
        for key, value in section.items():
            self._settings[key] = value

    def get(self, key, default=None):
        """Возвращает значение настройки по ключу."""
        return self._settings.get(key, default)

    def reload(self):
        """Перечитывает конфигурацию с диска."""
        self._settings = dict(DEFAULT_SETTINGS)
        self._load_pyproject()
