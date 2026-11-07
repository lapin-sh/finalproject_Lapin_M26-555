"""Хранилище сервиса парсинга: кэш и история курсов."""

import json
import os
import tempfile

from valutatrade_hub.infra.settings import SettingsLoader


class RatesStorage:
    """Читает и пишет rates.json (кэш) и exchange_rates.json (история)."""

    def __init__(self, rates_path=None, history_path=None):
        data_dir = SettingsLoader().get("data_dir", "data")
        self.rates_path = rates_path or os.path.join(data_dir, "rates.json")
        self.history_path = (
            history_path or os.path.join(data_dir, "exchange_rates.json")
        )

    def _atomic_write(self, path, data):
        """Пишет через временный файл и переименование."""
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def load_cache(self):
        """Возвращает кэш курсов или пустую структуру."""
        if not os.path.exists(self.rates_path):
            return {"pairs": {}, "last_refresh": None}
        with open(self.rates_path, encoding="utf-8") as file:
            return json.load(file)

    def save_cache(self, pairs, last_refresh):
        """Сохраняет снимок текущих курсов."""
        self._atomic_write(
            self.rates_path, {"pairs": pairs, "last_refresh": last_refresh}
        )

    def append_history(self, records):
        """Добавляет записи в историю, пропуская дубли по id."""
        history = []
        if os.path.exists(self.history_path):
            with open(self.history_path, encoding="utf-8") as file:
                history = json.load(file)
        known_ids = {record["id"] for record in history}
        for record in records:
            if record["id"] not in known_ids:
                history.append(record)
                known_ids.add(record["id"])
        self._atomic_write(self.history_path, history)
