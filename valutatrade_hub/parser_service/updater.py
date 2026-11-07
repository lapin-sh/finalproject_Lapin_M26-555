"""Координатор обновления курсов: RatesUpdater."""

import logging
import time
from datetime import datetime, timezone

from valutatrade_hub.parser_service.storage import RatesStorage

parser_log = logging.getLogger("parser")


def utc_now_iso():
    """Возвращает текущее время UTC в формате ISO."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RatesUpdater:
    """Опрашивает API-клиентов и сохраняет объединенный результат."""

    def __init__(self, clients, storage=None):
        self.clients = clients
        self.storage = storage or RatesStorage()

    def run_update(self):
        """Обновляет курсы: сбор, объединение, сохранение, логирование."""
        print("INFO: Starting rates update...")
        parser_log.info("Starting rates update")
        merged = {}
        history_records = []
        had_errors = False
        for client in self.clients:
            started = time.monotonic()
            try:
                rates = client.fetch_rates()
            except Exception as error:
                had_errors = True
                reason = getattr(error, "reason", error)
                print(
                    f"ERROR: Failed to fetch from {client.source_name}: {reason}"
                )
                parser_log.error(
                    "Failed to fetch from %s: %s", client.source_name, error
                )
                continue
            elapsed_ms = int((time.monotonic() - started) * 1000)
            print(
                f"INFO: Fetching from {client.source_name}... "
                f"OK ({len(rates)} rates)"
            )
            parser_log.info(
                "Fetched %d rates from %s in %d ms",
                len(rates), client.source_name, elapsed_ms,
            )
            timestamp = utc_now_iso()
            for pair, rate in rates.items():
                merged[pair] = {
                    "rate": rate,
                    "updated_at": timestamp,
                    "source": client.source_name,
                }
                from_code, to_code = pair.split("_")
                history_records.append({
                    "id": f"{from_code}_{to_code}_{timestamp}",
                    "from_currency": from_code,
                    "to_currency": to_code,
                    "rate": rate,
                    "timestamp": timestamp,
                    "source": client.source_name,
                    "meta": {"request_ms": elapsed_ms},
                })
        old_cache = self.storage.load_cache()
        if merged:
            # обновляем только полученные пары, прежние значения не теряем
            all_pairs = dict(old_cache.get("pairs", {}))
            all_pairs.update(merged)
            last_refresh = utc_now_iso()
            print(f"INFO: Writing {len(merged)} rates to data/rates.json...")
            self.storage.save_cache(all_pairs, last_refresh)
            self.storage.append_history(history_records)
        else:
            last_refresh = old_cache.get("last_refresh")
        parser_log.info("Update finished: %d rates, errors=%s", len(merged), had_errors)
        if had_errors:
            print("Update completed with errors. Check logs/parser.log for details.")
        else:
            print(
                f"Update successful. Total rates updated: {len(merged)}. "
                f"Last refresh: {last_refresh.replace('Z', '')}"
            )
        return {
            "total": len(merged),
            "last_refresh": last_refresh,
            "errors": had_errors,
        }


def build_updater(only_source=None):
    """Собирает updater с настроенными клиентами."""
    from valutatrade_hub.parser_service.api_clients import (
        CoinGeckoClient,
        ExchangeRateApiClient,
    )

    clients = []
    if only_source in (None, "coingecko"):
        clients.append(CoinGeckoClient())
    if only_source in (None, "exchangerate"):
        clients.append(ExchangeRateApiClient())
    return RatesUpdater(clients)


def run_update():
    """Запускает обновление всеми клиентами по умолчанию."""
    return build_updater().run_update()
