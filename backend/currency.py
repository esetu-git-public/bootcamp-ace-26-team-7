# backend/currency.py

import time
import requests

FRANKFURTER_URL = "https://api.frankfurter.app/latest"

# Simple in-memory cache: {currency_code: (rate, fetched_at_timestamp)}
_rate_cache = {}
CACHE_TTL_SECONDS = 3600  # refresh rates every 1 hour


def get_exchange_rate(target_currency: str, base_currency: str = "USD") -> float:
    """
    Returns the exchange rate to convert 1 unit of base_currency into target_currency.
    e.g. get_exchange_rate("INR") -> ~83.2 (1 USD = 83.2 INR)
    Falls back to 1.0 (no conversion) if the API call fails.
    """
    target_currency = target_currency.upper()

    if target_currency == base_currency.upper():
        return 1.0

    cached = _rate_cache.get(target_currency)
    if cached and (time.time() - cached[1] < CACHE_TTL_SECONDS):
        return cached[0]

    try:
        response = requests.get(
            FRANKFURTER_URL,
            params={"from": base_currency, "to": target_currency},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        rate = data["rates"][target_currency]
        _rate_cache[target_currency] = (rate, time.time())
        return rate
    except Exception:
        # Fail safe: if the API is down, don't crash the estimator —
        # just return 1.0 so the caller can decide how to handle it.
        return 1.0


def convert_amount(amount: float, target_currency: str, base_currency: str = "USD") -> float:
    rate = get_exchange_rate(target_currency, base_currency)
    return round(amount * rate, 2)