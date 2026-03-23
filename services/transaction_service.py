"""
services/transaction_service.py
All business logic for creating, reading, updating and deleting transactions.
UI never touches the database directly — it only calls functions from here.
"""

import calendar
from datetime import date
from datetime import date as date_type
from typing import Optional

from main import logger
from models.models import Transaction, Category, User
from db.database import db


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

    Usage:
        tx = add_transaction(user, "expense", 50000, category=groceries_cat)
        # → saves a 500.00 expense to the database
    """
    if amount_cents <= 0:
        raise ValueError("Amount must be greater than zero")
    if type not in ("income", "expense"):
        raise ValueError("Type must be 'income' or 'expense'")

    with db:
        tx = Transaction.create(
            user=user,
            type=type,
            amount_cents=amount_cents,
            category=category,
            date=tx_date or date_type.today(),
            note=note.strip(),
            is_recurring=is_recurring,
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
    if amount_cents is not None:
        if amount_cents <= 0:
            raise ValueError("Amount must be greater than zero")
        tx.amount_cents = amount_cents
    if category is not None:
        tx.category = category
    if tx_date is not None:
        tx.date = tx_date
    if note is not None:
        tx.note = note.strip()
    if type is not None:
        if type not in ("income", "expense"):
            raise ValueError("Type must be 'income' or 'expense'")
        tx.type = type

    with db:
        tx.save()
    return tx


def delete_transaction(tx: Transaction) -> None:
    """Permanently deletes a transaction."""
    with db:
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
    """Returns all transactions marked as recurring."""
    return list(Transaction.select().where(
        Transaction.user         == user,
        Transaction.is_recurring == True,
    ).order_by(Transaction.date.desc()))


def create_recurring_for_month(user, year: int, month: int) -> int:
    """
    Checks all recurring transactions and creates copies
    for the given month if they don't exist yet.
    Returns the number of transactions created.

    Called automatically on app startup from main.py.
    Safe to call multiple times — won't create duplicates.
    """
    recurring = get_recurring_transactions(user)
    created   = 0

    for tx in recurring:
        # Calculate correct date for this month
        target_date = get_safe_date(tx.date, year, month)

        # Check if this recurring transaction already exists this month
        # Match by category + amount + note to identify duplicates
        exists = Transaction.select().where(
            Transaction.user         == user,
            Transaction.category     == tx.category,
            Transaction.amount_cents == tx.amount_cents,
            Transaction.note         == tx.note,
            Transaction.date.between(
                date(year, month, 1),
                date(year, month, calendar.monthrange(year, month)[1])
            ),
        ).exists()

        if not exists:
            with db:
                Transaction.create(
                    user         = user,
                    type         = tx.type,
                    amount_cents = tx.amount_cents,
                    category     = tx.category,
                    date         = target_date,
                    note         = tx.note,
                    is_recurring = True,  # copy is not recurring itself
                )
            created += 1
            logger.info(
                f"Auto-created recurring: '{tx.note}' "
                f"{tx.amount_cents} cents → {target_date}"
            )

    return created