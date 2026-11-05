"""
services/currency_service.py
Purchases in other currencies, converted to the main currency.

Rates are entered by hand (Settings): 1 EUR = 3.95 ₪ is stored as "3.95".
A purchase is converted ONCE, when it is saved, with the rate of that moment,
and the rate is stored on the transaction — so changing a rate later never
changes past purchases, just like a bank statement.

All the arithmetic uses Decimal, never float:
  0.50 EUR × 1.15 = 0.575 → 0.58  (with float it comes out as 0.57)
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from db.database import db
from models.models import ExchangeRate, Transaction, User
from services.transaction_service import add_transaction

_CODE = re.compile(r"[A-Z]{3}")


def normalize_currency_code(code: str) -> str:
    """' eur ' → 'EUR'. Any three latin letters are allowed (PLN, HUF, …)."""
    code = (code or "").strip().upper()
    if not _CODE.fullmatch(code):
        raise ValueError(f"Currency code must be three letters, like EUR: {code!r}")
    return code


def parse_rate(value) -> Decimal:
    """
    '3,95' / '3.95' / Decimal('3.95') → Decimal('3.95').
    Raises ValueError for anything that isn't a positive finite number.
    """
    if isinstance(value, Decimal):
        rate = value
    else:
        text = str(value).strip().replace(" ", "").replace(",", ".")
        try:
            rate = Decimal(text)
        except InvalidOperation:
            raise ValueError(f"Not a number: {value!r}")
    if not rate.is_finite() or rate <= 0:
        raise ValueError(f"Exchange rate must be greater than zero: {value!r}")
    return rate


def format_rate(rate: Decimal) -> str:
    """Decimal('4.00') → '4', Decimal('3.950') → '3.95' — how a rate is stored and shown."""
    return format(rate.normalize(), "f")


def convert_cents(amount_cents: int, rate: Decimal) -> int:
    """
    Amount in the other currency → amount in the main currency, in cents.
    Rounds half up to a whole cent: 0.575 → 0.58. With float the product
    would be 57.4999… cents → 0.57, and Python's round() rounds 2.5 to 2.
    """
    exact = Decimal(amount_cents) * rate
    return int(exact.quantize(Decimal(1), rounding=ROUND_HALF_UP))


# ── Saved rates (Settings) ────────────────────────────────────────────────────

def set_rate(user: User, currency: str, rate) -> ExchangeRate:
    """Saves '1 <currency> = <rate> main currency', replacing the old rate if there was one."""
    code = normalize_currency_code(currency)
    if code == user.currency:
        raise ValueError(f"{code} is the main currency — it needs no exchange rate")
    text = format_rate(parse_rate(rate))

    with db:
        row = ExchangeRate.get_or_none(
            (ExchangeRate.user == user) & (ExchangeRate.currency == code))
        if row is None:
            row = ExchangeRate.create(user=user, currency=code, rate=text)
        else:
            row.rate = text
            row.updated_at = datetime.now()
            row.save()
    return row


def get_rate(user: User, currency: str) -> Optional[Decimal]:
    """The saved rate for this currency, or None if there is none."""
    row = ExchangeRate.get_or_none(
        (ExchangeRate.user == user) & (ExchangeRate.currency == normalize_currency_code(currency)))
    return Decimal(row.rate) if row else None


def get_rates(user: User) -> list[ExchangeRate]:
    """All saved rates of this user, sorted by currency code."""
    return list(ExchangeRate.select()
                .where(ExchangeRate.user == user)
                .order_by(ExchangeRate.currency))


def delete_rate(user: User, currency: str) -> bool:
    """Removes a saved rate. Past purchases keep the rate they were converted with."""
    with db:
        removed = (ExchangeRate.delete()
                   .where((ExchangeRate.user == user)
                          & (ExchangeRate.currency == normalize_currency_code(currency)))
                   .execute())
    return removed > 0


# ── Purchases in another currency ─────────────────────────────────────────────

def add_transaction_in_currency(
    user: User,
    type: str,
    amount_cents: int,
    currency: Optional[str] = None,
    rate=None,
    **kwargs,
) -> Transaction:
    """
    Adds a transaction entered in `currency`.
      - main currency (or None): saved as usual, nothing to convert
      - other currency: converted with `rate` if given (the rate of this one
        purchase, e.g. from the bank statement), otherwise with the saved rate

    Example (main currency ILS, saved rate 1 EUR = 3.95):
        add_transaction_in_currency(user, "expense", 2000, "EUR")
        → amount_cents=7900, currency="EUR", original_amount_cents=2000, exchange_rate="3.95"

    Other keyword arguments (category, tx_date, note, …) go to add_transaction.
    """
    if currency is None or normalize_currency_code(currency) == user.currency:
        return add_transaction(user, type, amount_cents, **kwargs)

    code = normalize_currency_code(currency)
    if rate is None:
        rate = get_rate(user, code)
        if rate is None:
            raise ValueError(f"No exchange rate for {code} — enter one for this purchase or in Settings")
    rate = parse_rate(rate)

    return add_transaction(
        user, type, convert_cents(amount_cents, rate),
        currency=code,
        original_amount_cents=amount_cents,
        exchange_rate=format_rate(rate),
        **kwargs,
    )