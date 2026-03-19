"""
tests/test_services.py
Unit tests for all three services.
Uses in-memory SQLite — never touches your real budget.db
Run with: pytest tests/ -v
"""

import pytest
from datetime import date
from peewee import SqliteDatabase
from models.models import ALL_MODELS, User, Category, Transaction, Budget, Goal

test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def setup_db():
    """Before each test: fresh in-memory database."""
    test_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(ALL_MODELS)
    yield
    test_db.drop_tables(ALL_MODELS)
    test_db.close()


@pytest.fixture
def user():
    return User.create(name="Test User", currency="USD")

@pytest.fixture
def groceries(user):
    return Category.create(user=user, name="Groceries", icon="🛒", color="#16A34A", type="expense")

@pytest.fixture
def salary_cat(user):
    return Category.create(user=user, name="Salary", icon="💼", color="#16A34A", type="income")


# ── TransactionService ────────────────────────────────────────────────────────

class TestTransactionService:

    def test_add_expense(self, user, groceries):
        from services.transaction_service import add_transaction
        tx = add_transaction(user, "expense", 50000, category=groceries)
        assert tx.id is not None
        assert tx.amount_cents == 50000
        assert tx.type == "expense"

    def test_add_income(self, user, salary_cat):
        from services.transaction_service import add_transaction
        tx = add_transaction(user, "income", 200000, category=salary_cat)
        assert tx.type == "income"

    def test_invalid_amount_raises(self, user):
        from services.transaction_service import add_transaction
        with pytest.raises(ValueError):
            add_transaction(user, "expense", 0)

    def test_invalid_type_raises(self, user):
        from services.transaction_service import add_transaction
        with pytest.raises(ValueError):
            add_transaction(user, "transfer", 10000)

    def test_get_transactions_returns_all(self, user, groceries):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries)
        add_transaction(user, "expense", 20000, category=groceries)
        assert len(get_transactions(user)) == 2

    def test_get_transactions_filter_by_type(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries)
        add_transaction(user, "income",  20000, category=salary_cat)
        expenses = get_transactions(user, type="expense")
        assert len(expenses) == 1
        assert expenses[0].amount_cents == 10000

    def test_get_transactions_filter_by_date(self, user, groceries):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 20000, category=groceries, tx_date=date(2025, 4, 1))
        march = get_transactions(user, date_from=date(2025, 3, 1), date_to=date(2025, 3, 31))
        assert len(march) == 1
        assert march[0].amount_cents == 10000

    def test_update_transaction(self, user, groceries):
        from services.transaction_service import add_transaction, update_transaction
        tx = add_transaction(user, "expense", 10000, category=groceries)
        updated = update_transaction(tx, amount_cents=25000, note="Updated")
        assert updated.amount_cents == 25000
        assert updated.note == "Updated"

    def test_delete_transaction(self, user, groceries):
        from services.transaction_service import add_transaction, delete_transaction, get_transactions
        tx = add_transaction(user, "expense", 10000, category=groceries)
        delete_transaction(tx)
        assert len(get_transactions(user)) == 0

    def test_get_totals(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, get_totals
        add_transaction(user, "income",  200000, category=salary_cat)
        add_transaction(user, "expense",  80000, category=groceries)
        totals = get_totals(user)
        assert totals["income_cents"]  == 200000
        assert totals["expense_cents"] ==  80000
        assert totals["balance_cents"] == 120000


# ── BudgetService ─────────────────────────────────────────────────────────────

class TestBudgetService:

    def test_set_budget(self, user, groceries):
        from services.budget_service import set_budget, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2025, month=3)
        budgets = get_budgets(user, 2025, 3)
        assert len(budgets) == 1
        assert budgets[0].limit_cents == 50000

    def test_update_existing_budget(self, user, groceries):
        from services.budget_service import set_budget, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2025, month=3)
        set_budget(user, groceries, limit_cents=75000, year=2025, month=3)
        budgets = get_budgets(user, 2025, 3)
        assert len(budgets) == 1
        assert budgets[0].limit_cents == 75000

    def test_budget_status_ok(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        add_transaction(user, "expense", 50000, category=groceries, tx_date=date(2025, 3, 15))
        row = get_budget_status(user, 2025, 3)[0]
        assert row["spent_cents"] == 50000
        assert row["percent"]     == 50.0
        assert row["status"]      == "ok"

    def test_budget_status_warning(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        add_transaction(user, "expense", 85000, category=groceries, tx_date=date(2025, 3, 15))
        assert get_budget_status(user, 2025, 3)[0]["status"] == "warning"

    def test_budget_status_danger(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        add_transaction(user, "expense", 120000, category=groceries, tx_date=date(2025, 3, 15))
        assert get_budget_status(user, 2025, 3)[0]["status"] == "danger"

    def test_copy_from_previous_month(self, user, groceries):
        from services.budget_service import set_budget, copy_budgets_from_previous_month, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2025, month=3)
        copied = copy_budgets_from_previous_month(user, year=2025, month=4)
        assert copied == 1
        assert get_budgets(user, 2025, 4)[0].limit_cents == 50000


# ── AnalyticsService ──────────────────────────────────────────────────────────

class TestAnalyticsService:

    def test_get_balance(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_balance
        add_transaction(user, "income",  300000, category=salary_cat)
        add_transaction(user, "expense", 120000, category=groceries)
        b = get_balance(user)
        assert b["income_cents"]  == 300000
        assert b["expense_cents"] == 120000
        assert b["balance_cents"] == 180000

    def test_get_spending_by_category(self, user, groceries):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_spending_by_category
        add_transaction(user, "expense", 30000, category=groceries, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 20000, category=groceries, tx_date=date(2025, 3, 15))
        result = get_spending_by_category(user, date(2025, 3, 1), date(2025, 3, 31))
        assert result[0]["spent_cents"] == 50000
        assert result[0]["percent"]     == 100.0

    def test_get_daily_totals_fills_empty_days(self, user, groceries):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_daily_totals
        add_transaction(user, "expense", 10000, category=groceries, tx_date=date(2025, 3, 1))
        result = get_daily_totals(user, date(2025, 3, 1), date(2025, 3, 3))
        assert len(result) == 3
        assert result[0]["amount_cents"] == 10000
        assert result[1]["amount_cents"] == 0
        assert result[2]["amount_cents"] == 0

    def test_get_month_summary(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_month_summary
        add_transaction(user, "income",  200000, category=salary_cat, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense",  80000, category=groceries,  tx_date=date(2025, 3, 10))
        s = get_month_summary(user, 2025, 3)
        assert s["income_cents"]  == 200000
        assert s["expense_cents"] ==  80000
        assert s["balance_cents"] == 120000
        assert "top_categories"   in s
        assert "daily_avg_cents"  in s