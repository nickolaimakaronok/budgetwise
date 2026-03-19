"""
services/transaction_service.py
All business logic for creating, reading, updating and deleting transactions.
UI never touches the database directly — it only calls functions from here.
"""

from datetime import date as date_type
from typing import Optional
from models.models import Transaction, Category, User
from db.database import db


def add_transaction(
    user: User,
    type: str,
    amount_cents: int,
    category: Optional[Category] = None,
    tx_date: Optional[date_type] = None,
    note: str = "",
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