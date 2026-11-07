"""Доступ к JSON-хранилищу данных (паттерн Singleton)."""

import json
import os
import tempfile

from valutatrade_hub.infra.settings import SettingsLoader

USERS_FILE = "users.json"
PORTFOLIOS_FILE = "portfolios.json"
RATES_FILE = "rates.json"
HISTORY_FILE = "exchange_rates.json"


class DatabaseManager:
    """Единая точка чтения и записи JSON-файлов проекта.

    Singleton реализован через __new__ по тем же причинам, что и SettingsLoader:
    просто, читабельно и гарантирует один экземпляр на процесс.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._data_dir = SettingsLoader().get("data_dir", "data")
            os.makedirs(instance._data_dir, exist_ok=True)
            cls._instance = instance
        return cls._instance

    def _path(self, name):
        """Собирает путь к файлу хранилища."""
        return os.path.join(self._data_dir, name)

    def load(self, name, default=None):
        """Читает JSON-файл, при его отсутствии возвращает default."""
        path = self._path(name)
        if not os.path.exists(path):
            return default
        try:
            with open(path, encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return default

    def save(self, name, data):
        """Атомарно сохраняет данные: временный файл, затем замена."""
        path = self._path(name)
        fd, tmp_path = tempfile.mkstemp(dir=self._data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
