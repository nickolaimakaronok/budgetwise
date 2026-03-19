"""
utils/formatters.py
Formatting helpers for money, dates, and other display values.
"""

from datetime import date, datetime


CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "RUB": "₽",
    "ILS": "₪",  # Israeli Shekel
}

_current_currency = "USD"


def set_currency(currency: str):
    global _current_currency
    _current_currency = currency


def format_money(amount_cents: int, show_sign: bool = False) -> str:
    """
    Formats cents into a human-readable string.
    format_money(150050)  →  "1 500.50 $"
    format_money(-50000)  →  "-500.00 $"
    """
    symbol = CURRENCY_SYMBOLS.get(_current_currency, _current_currency)
    amount = amount_cents / 100
    sign = "+" if show_sign and amount > 0 else ""
    formatted = f"{amount:,.2f}".replace(",", " ")
    return f"{sign}{formatted} {symbol}"


def format_money_short(amount_cents: int) -> str:
    """Short format for the dashboard: 1 500 $ (no decimals if amount is whole)."""
    symbol = CURRENCY_SYMBOLS.get(_current_currency, _current_currency)
    amount = amount_cents / 100
    if amount == int(amount):
        formatted = f"{int(amount):,}".replace(",", " ")
        return f"{formatted} {symbol}"
    return format_money(amount_cents)


def parse_money(text: str) -> int:
    """
    Parses a user-entered string into cents.
    "1500"    → 150000
    "1500.50" → 150050
    "1 500.5" → 150050
    """
    cleaned = text.strip().replace(" ", "").replace(",", ".")
    # Strip currency symbols
    for sym in CURRENCY_SYMBOLS.values():
        cleaned = cleaned.replace(sym, "")
    try:
        return round(float(cleaned) * 100)
    except ValueError:
        raise ValueError(f"Invalid amount format: '{text}'")


def format_date(d: date, fmt: str = "%d.%m.%Y") -> str:
    """date → "19.03.2025" """
    return d.strftime(fmt)


def format_date_short(d: date) -> str:
    """date → "19 Mar" """
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{d.day} {months[d.month - 1]}"


def parse_date(text: str) -> date:
    """Parses a date string in DD.MM.YYYY format."""
    return datetime.strptime(text.strip(), "%d.%m.%Y").date()


def month_name(month: int, year: int) -> str:
    """1, 2025 → "January 2025" """
    names = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]
    return f"{names[month - 1]} {year}"


def percent(part: int, total: int) -> float:
    """Returns percentage, safely handles division by zero."""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 1)
