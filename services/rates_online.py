"""
services/rates_online.py
Exchange rates from the internet: Frankfurter (api.frankfurter.dev) — free,
no key, daily rates from central banks, any past date too.

It only fills the saved rates (the same ExchangeRate table as Settings).
Past purchases keep the rate they were converted with — nothing here
touches a transaction.

Without internet every function raises RatesUnavailable, and the caller
keeps the last saved rate.
"""

import http.client
import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional
from urllib.parse import urlencode

from models.models import User
from services.currency_service import get_rates, normalize_currency_code, set_rate
from utils.constants import APP_VERSION

API_URL = "https://api.frankfurter.dev/v2/rates"
SOURCE_NAME = "Frankfurter"
TIMEOUT_SECONDS = 5
RATE_DIGITS = 6        # 1 / 0.2531646 = 3.95000 — six significant digits are plenty


class RatesUnavailable(Exception):
    """No internet, the service is down, or its answer can't be read."""


@dataclass
class OnlineRates:
    rates: dict                       # {"EUR": Decimal("3.95")} — 1 EUR costs 3.95 in the main currency
    on: Optional[date] = None         # the day the rates are for (a weekend gives the last working day)


@dataclass
class UpdateResult:
    updated: dict = field(default_factory=dict)    # {"EUR": Decimal("3.95")}
    missing: list = field(default_factory=list)    # saved currencies the service doesn't know
    on: Optional[date] = None


# ── Network ───────────────────────────────────────────────────────────────────

def _ssl_context() -> ssl.SSLContext:
    """
    certifi brings its own list of trusted certificates. The packaged app
    (PyInstaller) often can't find the system one and fails with
    CERTIFICATE_VERIFY_FAILED; from source the system list works too.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _http_get(url: str) -> bytes:
    """One GET request. Tests replace this function — they never use the network."""
    request = urllib.request.Request(url, headers={"User-Agent": f"BudgetWise/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=_ssl_context()) as response:
        return response.read()


# ── Reading the answer ────────────────────────────────────────────────────────

def _parse(payload) -> tuple[dict, Optional[date]]:
    """
    How much ONE main-currency unit is worth in each currency: {"EUR": Decimal("0.2532")}.
    Frankfurter v2 answers with a list of rows:
        [{"date": "2026-11-06", "base": "ILS", "quote": "EUR", "rate": 0.2532}, ...]
    The older v1 shape {"date": ..., "rates": {"EUR": 0.2532}} is read too.
    """
    if isinstance(payload, dict) and isinstance(payload.get("rates"), dict):
        rows = [{"quote": code, "rate": rate, "date": payload.get("date")}
                for code, rate in payload["rates"].items()]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise RatesUnavailable("Unexpected answer from the rates service")

    per_main, on = {}, None
    for row in rows:
        if not isinstance(row, dict):
            continue
        code, value = str(row.get("quote", "")).upper(), row.get("rate")
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, ValueError):
            continue
        if len(code) == 3 and rate.is_finite() and rate > 0:   # skips crypto like "USDT"
            per_main[code] = rate
        if on is None and row.get("date"):
            try:
                on = date.fromisoformat(str(row["date"]))
            except ValueError:
                pass
    return per_main, on


def _invert(per_main: Decimal) -> Decimal:
    """1 ILS = 0.2531646 EUR  →  1 EUR = 3.95 ILS (exact Decimal, six significant digits)."""
    return Context(prec=RATE_DIGITS, rounding=ROUND_HALF_UP).divide(Decimal(1), per_main)


# ── Public functions ──────────────────────────────────────────────────────────

def fetch_rates(main: str, codes, on_date: Optional[date] = None) -> OnlineRates:
    """
    Rates of `codes` in the main currency: fetch_rates("ILS", ["EUR"]) → {"EUR": 3.95}.
    on_date: the rate of that day (an old receipt); None = the latest.
    Currencies the service doesn't know are simply not in the result.
    """
    main = normalize_currency_code(main)
    wanted = {normalize_currency_code(c) for c in codes} - {main}
    params = {"base": main}            # all quotes for this base — one request, and an
    if on_date is not None:            # unknown currency can't make the whole request fail
        params["date"] = on_date.isoformat()

    try:
        raw = _http_get(f"{API_URL}?{urlencode(params)}")
        payload = json.loads(raw, parse_float=Decimal)
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError) as e:
        # offline, timeout, HTTP 4xx/5xx, a cut-off answer, not JSON
        raise RatesUnavailable(str(e)) from e

    per_main, on = _parse(payload)
    rates = {code: _invert(per_main[code]) for code in sorted(wanted) if code in per_main}
    return OnlineRates(rates=rates, on=on)


def fetch_rate(main: str, code: str, on_date: Optional[date] = None) -> Decimal:
    """One currency, for the Add window. RatesUnavailable if it can't be had."""
    result = fetch_rates(main, [code], on_date)
    code = normalize_currency_code(code)
    if code not in result.rates:
        raise RatesUnavailable(f"No rate for {code}")
    return result.rates[code]


def update_saved_rates(user: User) -> UpdateResult:
    """
    Refreshes every rate saved in Settings with today's rate.
    Writes ONLY the saved rates — past purchases keep their own rate.
    RatesUnavailable without internet; then nothing is changed.
    """
    codes = [row.currency for row in get_rates(user)]
    if not codes:
        return UpdateResult()

    result = fetch_rates(user.currency, codes)
    for code, rate in result.rates.items():
        set_rate(user, code, rate)
    missing = [c for c in codes if c not in result.rates]
    return UpdateResult(updated=result.rates, missing=missing, on=result.on)