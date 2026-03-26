"""
services/analytics_service.py
Business logic for the Analytics page — balance, category breakdown, trends.
"""

from datetime import date, timedelta
from calendar import monthrange
from models.models import Transaction, Category, User
from db.database import db


def get_balance(user: User) -> dict:
    """
    Returns all-time balance.

    Returns:
        {
            "income_cents":  500000,
            "expense_cents": 320000,
            "balance_cents": 180000,
        }
    """
    txs     = list(Transaction.select().where(Transaction.user == user))
    income  = sum(t.amount_cents for t in txs if t.type == "income")
    expense = sum(t.amount_cents for t in txs if t.type == "expense")

    return {
        "income_cents":  income,
        "expense_cents": expense,
        "balance_cents": income - expense,
    }


def get_spending_by_category(
    user: User,
    date_from: date,
    date_to: date,
) -> list[dict]:
    """
    Returns spending broken down by category for a time period.
    Used for the pie chart on the Analytics page.

    Returns sorted list (largest first):
        [
            {
                "category":    <Category>,
                "spent_cents": 85000,
                "percent":     42.5,
                "color":       "#16A34A",
                "icon":        "🛒",
            },
            ...
        ]
    """
    txs = list(
        Transaction
        .select()
        .where(
            Transaction.user == user,
            Transaction.type == "expense",
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
    )

    totals: dict[int, int] = {}
    total_spent = 0

    for tx in txs:
        total_spent += tx.amount_cents
        if tx.category_id is not None:
            totals[tx.category_id] = totals.get(tx.category_id, 0) + tx.amount_cents

    if not totals:
        return []

    categories = {
        c.id: c for c in Category.select().where(Category.id << list(totals.keys()))
    }

    result = []
    for cat_id, spent in totals.items():
        cat = categories.get(cat_id)
        if cat is None:
            continue
        result.append({
            "category":    cat,
            "spent_cents": spent,
            "percent":     round(spent / total_spent * 100, 1) if total_spent > 0 else 0.0,
            "color":       cat.color,
            "icon":        cat.icon,
        })

    result.sort(key=lambda x: x["spent_cents"], reverse=True)
    return result


def get_daily_totals(
    user: User,
    date_from: date,
    date_to: date,
    type: str = "expense",
) -> list[dict]:
    """
    Returns daily totals for a period. Used for the bar chart.

    Returns:
        [
            {"date": date(2025, 3, 1), "amount_cents": 12000},
            {"date": date(2025, 3, 2), "amount_cents": 0},
            ...
        ]
    """
    txs = list(
        Transaction
        .select()
        .where(
            Transaction.user == user,
            Transaction.type == type,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
    )

    by_date: dict[date, int] = {}
    for tx in txs:
        by_date[tx.date] = by_date.get(tx.date, 0) + tx.amount_cents

    result  = []
    current = date_from
    while current <= date_to:
        result.append({"date": current, "amount_cents": by_date.get(current, 0)})
        current += timedelta(days=1)

    return result




def get_monthly_totals(user: User, year: int) -> list[dict]:
    """
    Returns income and expense totals for each month of a year.
    Used for the year-overview bar chart.
    """
    txs = list(
        Transaction
        .select()
        .where(
            Transaction.user == user,
            Transaction.date >= date(year, 1, 1),
            Transaction.date <= date(year, 12, 31),
        )
    )

    by_month: dict[int, dict] = {
        m: {"month": m, "income_cents": 0, "expense_cents": 0}
        for m in range(1, 13)
    }
    for tx in txs:
        m = tx.date.month
        if tx.type == "income":
            by_month[m]["income_cents"] += tx.amount_cents
        else:
            by_month[m]["expense_cents"] += tx.amount_cents

    return list(by_month.values())


def get_top_categories(
    user: User,
    date_from: date,
    date_to: date,
    top_n: int = 5,
) -> list[dict]:
    """Returns the top N spending categories. Used on the Dashboard."""
    return get_spending_by_category(user, date_from, date_to)[:top_n]


def get_month_summary(user: User, year: int, month: int) -> dict:
    """
    Full summary for one month. Used on the Dashboard.

    Returns:
        {
            "income_cents":    200000,
            "expense_cents":   145000,
            "balance_cents":    55000,
            "top_categories":  [...],
            "days_left":        12,
            "daily_avg_cents":  4833,
        }
    """
    last_day  = monthrange(year, month)[1]
    date_from = date(year, month, 1)
    date_to   = date(year, month, last_day)

    txs     = list(Transaction.select().where(
        Transaction.user == user,
        Transaction.date >= date_from,
        Transaction.date <= date_to,
    ))
    income  = sum(t.amount_cents for t in txs if t.type == "income")
    expense = sum(t.amount_cents for t in txs if t.type == "expense")

    today       = date.today()
    days_passed = (min(today, date_to) - date_from).days + 1
    days_left   = max(0, (date_to - today).days)
    daily_avg   = expense // days_passed if days_passed > 0 else 0

    return {
        "income_cents":    income,
        "expense_cents":   expense,
        "balance_cents":   income - expense,
        "top_categories":  get_top_categories(user, date_from, date_to, top_n=3),
        "days_left":       days_left,
        "daily_avg_cents": daily_avg,
    }


def get_yearly_totals(user, year: int) -> list[dict]:
    """
    Returns monthly income and expense totals for a given year.

    Returns list of 12 dicts:
    [
        {"month": 1, "income": 350000, "expense": 146000},
        ...
    ]
    """
    monthly = get_monthly_totals(user, year)
    return [
        {
            "month":   m["month"],
            "income":  m["income_cents"],
            "expense": m["expense_cents"],
        }
        for m in monthly
    ]