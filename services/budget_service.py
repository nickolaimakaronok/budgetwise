"""
services/budget_service.py
Business logic for monthly budget limits.
"""

from datetime import date
from typing import Optional
from models.models import Budget, Category, Transaction, User
from db.database import db


def set_budget(
    user: User,
    category: Category,
    limit_cents: int,
    year: int,
    month: int,
) -> Budget:
    """
    Creates or updates a budget limit for a category in a given month.

    Usage:
        set_budget(user, groceries_cat, limit_cents=50000, year=2025, month=3)
        # → sets a 500.00 limit for Groceries in March 2025
    """
    if limit_cents <= 0:
        raise ValueError("Budget limit must be greater than zero")
    if not (1 <= month <= 12):
        raise ValueError("Month must be between 1 and 12")

    with db:
        budget, created = Budget.get_or_create(
            user=user,
            category=category,
            period_year=year,
            period_month=month,
            defaults={"limit_cents": limit_cents},
        )
        if not created:
            budget.limit_cents = limit_cents
            budget.save()

    return budget


def get_budgets(user: User, year: int, month: int) -> list[Budget]:
    """Returns all budget limits set for a given month."""
    return list(
        Budget
        .select(Budget, Category)
        .join(Category)
        .where(
            Budget.user == user,
            Budget.period_year == year,
            Budget.period_month == month,
        )
        .order_by(Category.name)
    )


def delete_budget(budget: Budget) -> None:
    """Removes a budget limit for a category."""
    with db:
        budget.delete_instance()


def get_spending_by_category(user: User, year: int, month: int) -> dict[int, int]:
    """
    Calculates total spending per category for a given month.

    Returns:
        { category_id: spent_cents, ... }
    """
    date_from = date(year, month, 1)
    date_to = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    txs = (
        Transaction
        .select()
        .where(
            Transaction.user == user,
            Transaction.type == "expense",
            Transaction.date >= date_from,
            Transaction.date < date_to,
        )
    )

    totals: dict[int, int] = {}
    for tx in txs:
        if tx.category_id is not None:
            totals[tx.category_id] = totals.get(tx.category_id, 0) + tx.amount_cents

    return totals


def get_budget_status(user: User, year: int, month: int) -> list[dict]:
    """
    Main function for the Budget page.
    Returns each category with limit, spent, remaining, % used and status.

    Returns:
        [
            {
                "budget":      <Budget>,
                "category":    <Category>,
                "limit_cents": 50000,
                "spent_cents": 32000,
                "left_cents":  18000,
                "percent":     64.0,
                "status":      "ok",   # "ok" | "warning" | "danger"
            },
            ...
        ]
    """
    budgets  = get_budgets(user, year, month)
    spending = get_spending_by_category(user, year, month)
    result   = []

    for budget in budgets:
        spent  = spending.get(budget.category_id, 0)
        limit  = budget.limit_cents
        left   = limit - spent
        pct    = round((spent / limit) * 100, 1) if limit > 0 else 0.0
        status = "danger" if pct >= 100 else "warning" if pct >= 80 else "ok"

        result.append({
            "budget":      budget,
            "category":    budget.category,
            "limit_cents": limit,
            "spent_cents": spent,
            "left_cents":  left,
            "percent":     pct,
            "status":      status,
        })

    return result


def copy_budgets_from_previous_month(user: User, year: int, month: int) -> int:
    """
    Copies budget limits from the previous month into the current month.
    Returns the number of budgets copied.

    Usage:
        copied = copy_budgets_from_previous_month(user, year=2025, month=4)
        # → copies March 2025 limits into April 2025
    """
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)

    prev_budgets = get_budgets(user, prev_year, prev_month)
    for b in prev_budgets:
        set_budget(user, b.category, b.limit_cents, year, month)

    return len(prev_budgets)