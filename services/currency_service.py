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
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from db.database import db
from models.models import Budget, ExchangeRate, Goal, Transaction, User
from services.transaction_service import add_transaction, update_transaction

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



def update_transaction_in_currency(
    tx: Transaction,
    user: User,
    amount_cents: int,
    currency: Optional[str] = None,
    rate=None,
    **kwargs,
) -> Transaction:
    """
    Edit window: saves the transaction with `amount_cents` given in `currency`.
      - main currency (or None): the amount as is, the currency fields are cleared
      - another currency: converted with `rate` — the Edit window shows the
        purchase's own rate, so leaving it unchanged keeps the old conversion —
        or with the saved rate if no rate is given
    Other keyword arguments (category, tx_date, note, type) go to update_transaction.
    """
    if currency is None or normalize_currency_code(currency) == user.currency:
        converted = amount_cents
        fields = {"currency": None, "original_amount_cents": None, "exchange_rate": None}
    else:
        code = normalize_currency_code(currency)
        if rate is None:
            rate = get_rate(user, code)
            if rate is None:
                raise ValueError(f"No exchange rate for {code} — enter one for this purchase or in Settings")
        rate = parse_rate(rate)
        converted = convert_cents(amount_cents, rate)
        fields = {"currency": code, "original_amount_cents": amount_cents,
                  "exchange_rate": format_rate(rate)}

    # One UPDATE for the amount, the other fields and the currency fields together
    return update_transaction(tx, amount_cents=converted, currency_fields=fields, **kwargs)


def preview_conversion(amount_text: str, rate_text: str) -> Optional[int]:
    """
    For the live hint while typing: '20' and '3.95' → 7900 cents.
    None while either field is not a valid number yet.
    """
    from utils.formatters import parse_money
    try:
        return convert_cents(parse_money(amount_text), parse_rate(rate_text))
    except ValueError:
        return None

def recurring_copy_money(user: User, tpl: Transaction) -> dict:
    """
    The money fields of a new monthly copy of the recurring template `tpl`.
      - main currency: the template's amount, as before
      - another currency (a 10 € subscription): the same 10 €, converted with
        TODAY's saved rate — or with the template's own rate if that rate was deleted
    """
    if tpl.currency is None or tpl.currency == user.currency:
        return {"amount_cents": tpl.amount_cents}
    rate = get_rate(user, tpl.currency) or Decimal(tpl.exchange_rate)
    return {
        "amount_cents":          convert_cents(tpl.original_amount_cents, rate),
        "currency":              tpl.currency,
        "original_amount_cents": tpl.original_amount_cents,
        "exchange_rate":         format_rate(rate),
    }

# ── Changing the main currency ────────────────────────────────────────────────

MODE_RELABEL = "relabel"   # amounts were already in the new currency — only the symbol changes
MODE_CONVERT = "convert"   # moving to another currency — everything is converted with one rate


def _divide_cents(amount_cents: int, rate: Decimal) -> int:
    """Old main currency → new: amount / rate, half up. A positive amount never becomes 0."""
    result = int((Decimal(amount_cents) / rate).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return max(result, 1) if amount_cents > 0 else result


def _computed_rate(value: Decimal) -> str:
    """A rate we calculated (1/3.95, a cross-rate) — kept to 8 significant digits: '0.25316456'."""
    return format_rate(Context(prec=8, rounding=ROUND_HALF_UP).plus(value))


def _backup_before_change() -> None:
    """A backup that is never rotated away, made before every amount is rewritten."""
    from db.backup import create_backup
    from db.database import DB_PATH
    create_backup(DB_PATH, prefix="before_currency_change_")


def change_main_currency(user: User, new_currency: str, mode: str, rate=None) -> dict:
    """
    Switches the main currency of `user`.

    MODE_RELABEL — the amounts were already in the new currency (the wrong one
      was picked at the start): only the symbol changes, every number stays.

    MODE_CONVERT — moving to another currency. `rate` is 1 NEW = rate OLD,
      e.g. 1 EUR = 3.95 ILS. In one database transaction (all or nothing):
        - a purchase made in the new currency gets back its exact original amount
        - every other amount — transactions, budgets, goals — is divided by rate
        - purchases in the old main currency remember it: 70 ₪ becomes
          17.72 € with currency="ILS" and original 70.00, so switching back is exact
        - saved rates become cross-rates (1 USD = 3.70 ₪ → 1 USD = 0.937 €);
          the rate of the new currency is removed, one for the old currency added
      A backup is made before anything changes.

    Returns how many rows were converted: {"transactions": n, "budgets": n, "goals": n}.
    """
    new_code = normalize_currency_code(new_currency)
    old_code = user.currency
    if new_code == old_code:
        raise ValueError(f"{new_code} is already the main currency")
    if mode not in (MODE_RELABEL, MODE_CONVERT):
        raise ValueError(f"Unknown mode: {mode!r}")

    database = Transaction._meta.database      # the database the models are bound to
    counts = {"transactions": 0, "budgets": 0, "goals": 0}

    if mode == MODE_RELABEL:
        with database.atomic():
            (ExchangeRate.delete()
             .where((ExchangeRate.user == user) & (ExchangeRate.currency == new_code))
             .execute())
            user.currency = new_code
            user.save()
        return counts

    switch = parse_rate(rate)
    _backup_before_change()

    with database.atomic():
        for tx in Transaction.select().where(Transaction.user == user):
            if tx.currency == new_code and tx.original_amount_cents is not None:
                # was paid in the new currency — the exact amount is known
                tx.amount_cents = tx.original_amount_cents
                tx.currency = tx.original_amount_cents = tx.exchange_rate = None
            elif tx.currency is None:
                # was in the old main currency — keep it as a purchase in that currency
                tx.currency = old_code
                tx.original_amount_cents = tx.amount_cents
                tx.exchange_rate = _computed_rate(Decimal(1) / switch)
                tx.amount_cents = _divide_cents(tx.amount_cents, switch)
            else:
                # a third currency — its rate becomes a cross-rate
                tx.exchange_rate = _computed_rate(Decimal(tx.exchange_rate) / switch)
                tx.amount_cents = _divide_cents(tx.amount_cents, switch)
            tx.save()
            counts["transactions"] += 1

        for budget in Budget.select().where(Budget.user == user):
            budget.limit_cents = _divide_cents(budget.limit_cents, switch)
            budget.save()
            counts["budgets"] += 1

        for goal in Goal.select().where(Goal.user == user):
            goal.target_cents = _divide_cents(goal.target_cents, switch)
            goal.current_cents = _divide_cents(goal.current_cents, switch)
            goal.save()
            counts["goals"] += 1

        for row in ExchangeRate.select().where(ExchangeRate.user == user):
            if row.currency == new_code:
                row.delete_instance()
            else:
                row.rate = _computed_rate(Decimal(row.rate) / switch)
                row.updated_at = datetime.now()
                row.save()
        ExchangeRate.create(user=user, currency=old_code,
                            rate=_computed_rate(Decimal(1) / switch))

        user.currency = new_code
        user.save()

    return counts