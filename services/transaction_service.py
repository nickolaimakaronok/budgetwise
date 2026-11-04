"""
services/transaction_service.py
All business logic for creating, reading, updating and deleting transactions.
UI never touches the database directly — it only calls functions from here.
"""

import calendar
from datetime import date
from datetime import date as date_type
from typing import Optional

import logging
logger = logging.getLogger(__name__)
from peewee import fn
from models.models import Transaction, Category, User
from db.database import db

def _first_of_month(d: date_type) -> date_type:
    """date(2026, 11, 23) → date(2026, 11, 1)"""
    return date(d.year, d.month, 1)


def _add_months(d: date_type, n: int) -> date_type:
    """First day of the month n months after d's month: (2026-11-23, 2) → 2027-01-01."""
    idx = d.year * 12 + (d.month - 1) + n
    return date(idx // 12, idx % 12 + 1, 1)


def add_transaction(
    user: User,
    type: str,
    amount_cents: int,
    category: Optional[Category] = None,
    tx_date: Optional[date_type] = None,
    note: str = "",
    is_recurring: bool = False
) -> Transaction:
    """
    Creates and saves a new transaction.
    With is_recurring=True it becomes the TEMPLATE of a monthly series:
    copies for the following months are made by create_recurring_for_month().

    Usage:
        tx = add_transaction(user, "expense", 50000, category=groceries_cat)
        # → saves a 500.00 expense to the database
    """
    if amount_cents <= 0:
        raise ValueError("Amount must be greater than zero")
    if type not in ("income", "expense"):
        raise ValueError("Type must be 'income' or 'expense'")

    tx_date = tx_date or date_type.today()
    with db:
        tx = Transaction.create(
            user=user,
            type=type,
            amount_cents=amount_cents,
            category=category,
            date=tx_date,
            note=note.strip(),
            is_recurring=is_recurring,
            # the template itself already covers its own month
            recurring_last_month=_first_of_month(tx_date) if is_recurring else None,
        )
    return tx


def get_transactions(
    user: User,
    date_from: Optional[date_type] = None,
    date_to: Optional[date_type] = None,
    type: Optional[str] = None,
    category: Optional[Category] = None,
    limit: int = 200,
) -> list[Transaction]:
    """
    Returns a filtered list of transactions, newest first.

    Usage:
        txs = get_transactions(user, date_from=date(2025,3,1))
        txs = get_transactions(user, type="expense", category=groceries_cat)
    """
    query = (
        Transaction
        .select()
        .where(Transaction.user == user)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(limit)
    )

    if date_from:
        query = query.where(Transaction.date >= date_from)
    if date_to:
        query = query.where(Transaction.date <= date_to)
    if type:
        query = query.where(Transaction.type == type)
    if category:
        query = query.where(Transaction.category == category)

    return list(query)


def get_recent_transactions(user: User, limit: int = 5) -> list[Transaction]:
    """Returns the N most recent transactions. Used on the dashboard."""
    return get_transactions(user, limit=limit)


def update_transaction(
    tx: Transaction,
    amount_cents: Optional[int] = None,
    category: Optional[Category] = None,
    tx_date: Optional[date_type] = None,
    note: Optional[str] = None,
    type: Optional[str] = None,
) -> Transaction:
    """
    Updates an existing transaction. Only updates fields that are passed in.

    Usage:
        update_transaction(tx, amount_cents=75000, note="Updated note")
    """
    fields = []  # only the columns that were actually edited
    if amount_cents is not None:
        if amount_cents <= 0:
            raise ValueError("Amount must be greater than zero")
        tx.amount_cents = amount_cents
        fields.append(Transaction.amount_cents)
    if category is not None:
        tx.category = category
        fields.append(Transaction.category)
    if tx_date is not None:
        tx.date = tx_date
        fields.append(Transaction.date)
    if note is not None:
        tx.note = note.strip()
        fields.append(Transaction.note)
    if type is not None:
        if type not in ("income", "expense"):
            raise ValueError("Type must be 'income' or 'expense'")
        tx.type = type
        fields.append(Transaction.type)

    # Save ONLY the edited columns. The Edit dialog holds an object loaded
    # earlier; a full save() would overwrite recurring_last_month (and the
    # other recurring columns) with stale values written meanwhile.
    if fields:
        with db:
            tx.save(only=fields)
    return tx


def delete_transaction(tx: Transaction) -> None:
    """
    Permanently deletes a transaction.
    Deleting the TEMPLATE of a recurring series doesn't end the series:
    its newest copy becomes the new template and the other copies move to it.
    (To stop a series, use set_recurring(tx, False) instead.)
    """
    with db:
        # re-read from the DB: the caller's object may be older than the
        # last create_recurring_for_month() run
        fresh = Transaction.get_or_none(Transaction.id == tx.id)
        if fresh is not None and fresh.is_recurring:
            copies = list(
                Transaction.select()
                .where(Transaction.recurring_parent == fresh.id)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
            )
            if copies:
                heir = copies[0]
                last = max(
                    fresh.recurring_last_month or _first_of_month(fresh.date),
                    _first_of_month(heir.date),
                )
                (Transaction
                 .update(is_recurring=True, recurring_parent=None, recurring_last_month=last)
                 .where(Transaction.id == heir.id)
                 .execute())
                (Transaction
                 .update(recurring_parent=heir.id)
                 .where((Transaction.recurring_parent == fresh.id) & (Transaction.id != heir.id))
                 .execute())
        tx.delete_instance()


def get_totals(
    user: User,
    date_from: Optional[date_type] = None,
    date_to: Optional[date_type] = None,
) -> dict:
    """
    Returns total income, total expenses, and net balance for a period.

    Returns:
        {
            "income_cents":  250000,
            "expense_cents": 180000,
            "balance_cents":  70000,
        }
    """
    txs = get_transactions(user, date_from=date_from, date_to=date_to)

    income  = sum(t.amount_cents for t in txs if t.type == "income")
    expense = sum(t.amount_cents for t in txs if t.type == "expense")

    return {
        "income_cents":  income,
        "expense_cents": expense,
        "balance_cents": income - expense,
    }



def get_safe_date(original_date, year: int, month: int):
    """
    Calculates the correct date for a recurring transaction.

    Handles all edge cases:
      - Jan 31 → Feb 28 (or Feb 29 in leap year)
      - Jan 31 → Apr 30 (April has 30 days)
      - Jan 15 → Feb 15 (normal case)

    Rules:
      1. If original was last day of its month → use last day of target month
      2. If original day > target month days  → use last day of target month
      3. Otherwise → use same day number
    """

    original_last_day = calendar.monthrange(
        original_date.year, original_date.month
    )[1]
    target_last_day = calendar.monthrange(year, month)[1]

    # Rule 1: was last day → always use last day of target
    if original_date.day == original_last_day:
        return date(year, month, target_last_day)

    # Rule 2: day doesn't exist in target month → use last day
    if original_date.day > target_last_day:
        return date(year, month, target_last_day)

    # Rule 3: normal case — same day number
    return date(year, month, original_date.day)


def get_recurring_transactions(user) -> list:
    """Returns the TEMPLATES of all active recurring series."""
    return list(Transaction.select().where(
        Transaction.user         == user,
        Transaction.is_recurring == True,
    ).order_by(Transaction.date.desc()))


def create_recurring_for_month(user, year: int, month: int) -> int:
    """
    Creates the missing monthly copies of every recurring series,
    up to and including (year, month). Returns the number created.

    Called automatically on app startup from main.py.
    Each template remembers the last month it generated (recurring_last_month):
      - nothing is duplicated, however often this runs;
      - a copy the user deleted is NOT re-created;
      - months the app wasn't opened in are caught up.
    Dates always come from the TEMPLATE's date, so the day doesn't drift.
    """
    target  = date(year, month, 1)
    created = 0

    with db:
        for tpl in get_recurring_transactions(user):
            last = tpl.recurring_last_month or _first_of_month(tpl.date)
            month_start = _add_months(last, 1)
            if month_start > target:
                continue                      # already up to date

            while month_start <= target:
                copy_date = get_safe_date(tpl.date, month_start.year, month_start.month)
                Transaction.create(
                    user             = user,
                    type             = tpl.type,
                    amount_cents     = tpl.amount_cents,
                    category         = tpl.category_id,
                    date             = copy_date,
                    note             = tpl.note,
                    is_recurring     = False,   # a copy is NOT a template
                    recurring_parent = tpl,
                )
                created += 1
                logger.info(
                    f"Auto-created recurring: '{tpl.note}' "
                    f"{tpl.amount_cents} cents → {copy_date}"
                )
                month_start = _add_months(month_start, 1)

            # move the counter — update just this column
            (Transaction
             .update(recurring_last_month=target)
             .where(Transaction.id == tpl.id)
             .execute())

    return created


def get_series_template(tx: Transaction):
    """The template of the series tx belongs to (tx itself if it is one), or None."""
    if tx.is_recurring:
        return tx
    if tx.recurring_parent_id:
        return Transaction.get_or_none(Transaction.id == tx.recurring_parent_id)
    return None


def is_series_active(tx: Transaction) -> bool:
    """True if tx is a template, or a copy whose template still repeats."""
    template = get_series_template(tx)
    return template is not None and template.is_recurring


def set_recurring(tx: Transaction, enabled: bool, today=None) -> Transaction:
    """
    Turns monthly repetition on or off for the series tx belongs to.
    Works on the template or on any of its copies. Returns the template.

    Turning it back on continues from the current month —
    months that passed while it was off are NOT back-filled.
    """
    today = today or date_type.today()

    with db:
        template = get_series_template(tx) or tx
        template = Transaction.get_by_id(template.id)   # fresh from the DB

        if not enabled:
            changes = {"is_recurring": False}
        elif not template.is_recurring:
            latest = (
                Transaction.select(fn.MAX(Transaction.date))
                .where((Transaction.recurring_parent == template.id) | (Transaction.id == template.id))
                .scalar()
            ) or template.date
            if isinstance(latest, str):
                latest = date.fromisoformat(latest)
            changes = {
                "is_recurring": True,
                "recurring_last_month": max(
                    template.recurring_last_month or _first_of_month(template.date),
                    _first_of_month(latest),
                    _add_months(today, -1),
                ),
            }
        else:
            return template                    # already on — nothing to do

        Transaction.update(**changes).where(Transaction.id == template.id).execute()
        for field, value in changes.items():
            setattr(template, field, value)
            if tx.id == template.id:
                setattr(tx, field, value)       # keep the caller's object in sync

    return template