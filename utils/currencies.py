"""
utils/currencies.py
The one list of currencies BudgetWise supports. Onboarding, Settings,
money formatting and CSV import all read it from here, so adding a
currency is one line in CURRENCIES.
"""

# code: (symbol, name) — the order here is the order in drop-down lists
CURRENCIES = {
    "USD": ("$",  "US Dollar"),
    "EUR": ("€",  "Euro"),
    "GBP": ("£",  "British Pound"),
    "RUB": ("₽",  "Russian Ruble"),
    "ILS": ("₪",  "Israeli Shekel"),
    "BYN": ("Br", "Belarusian Ruble"),
}

CURRENCY_CODES = list(CURRENCIES)


def currency_symbol(code: str) -> str:
    """'ILS' → '₪'. A code that isn't in the list is shown as itself ('PLN')."""
    entry = CURRENCIES.get(code)
    return entry[0] if entry else code


def currency_label(code: str) -> str:
    """'BYN' → 'Br — Belarusian Ruble', for drop-down lists."""
    symbol, name = CURRENCIES.get(code, (code, code))
    return f"{symbol} — {name}"