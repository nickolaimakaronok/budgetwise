"""
tests/test_full.py
Comprehensive test suite for the entire BudgetWise project.
Tests all services, models, formatters, and edge cases.
Run with: python -m pytest tests/test_full.py -v
"""

import pytest
from datetime import date, timedelta
from peewee import SqliteDatabase
from models.models import ALL_MODELS, User, Category, Transaction, Budget, Goal

# ── In-memory test database ───────────────────────────────────────────────────
test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def setup_db():
    """Fresh in-memory database before every single test."""
    test_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(ALL_MODELS)
    yield
    test_db.drop_tables(ALL_MODELS)
    test_db.close()


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def user():
    return User.create(name="Test User", currency="USD", month_start=1)


@pytest.fixture
def user2():
    return User.create(name="Second User", currency="EUR", month_start=1)


@pytest.fixture
def groceries(user):
    return Category.create(
        user=user, name="Groceries", icon="🛒",
        color="#16A34A", type="expense"
    )


@pytest.fixture
def transport(user):
    return Category.create(
        user=user, name="Transport", icon="🚇",
        color="#2563EB", type="expense"
    )


@pytest.fixture
def salary_cat(user):
    return Category.create(
        user=user, name="Salary", icon="💼",
        color="#16A34A", type="income"
    )


@pytest.fixture
def freelance_cat(user):
    return Category.create(
        user=user, name="Freelance", icon="💻",
        color="#2563EB", type="income"
    )


@pytest.fixture
def system_cat():
    """System category — no user (shared across all users)."""
    return Category.create(
        user=None, name="Other", icon="📦",
        color="#64748B", type="expense"
    )


# ─────────────────────────────────────────────────────────────────────────────
# MODEL TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestUserModel:

    def test_create_user(self):
        user = User.create(name="Alice", currency="USD")
        assert user.id is not None
        assert user.name == "Alice"
        assert user.currency == "USD"
        assert user.month_start == 1  # default value

    def test_user_default_currency(self):
        user = User.create(name="Bob")
        assert user.currency == "USD"

    def test_user_default_month_start(self):
        user = User.create(name="Carol")
        assert user.month_start == 1

    def test_multiple_users(self):
        User.create(name="Alice", currency="USD")
        User.create(name="Bob", currency="EUR")
        assert User.select().count() == 2

    def test_user_update(self, user):
        from db.database import db
        with db:
            user.name = "Updated Name"
            user.currency = "EUR"
            user.save()
        updated = User.get_by_id(user.id)
        assert updated.name == "Updated Name"
        assert updated.currency == "EUR"


class TestCategoryModel:

    def test_create_user_category(self, user):
        cat = Category.create(
            user=user, name="Coffee", icon="☕",
            color="#D97706", type="expense"
        )
        assert cat.id is not None
        assert cat.name == "Coffee"
        assert cat.is_archived == False

    def test_system_category_has_no_user(self, system_cat):
        assert system_cat.user_id is None

    def test_archive_category(self, user, groceries):
        from db.database import db
        with db:
            groceries.is_archived = True
            groceries.save()
        assert Category.get_by_id(groceries.id).is_archived == True

    def test_category_types(self, user, groceries, salary_cat):
        assert groceries.type == "expense"
        assert salary_cat.type == "income"

    def test_multiple_categories_per_user(self, user, groceries, transport, salary_cat):
        cats = list(Category.select().where(Category.user == user))
        assert len(cats) == 3


class TestTransactionModel:

    def test_create_transaction(self, user, groceries):
        tx = Transaction.create(
            user=user, type="expense",
            amount_cents=50000,
            category=groceries,
            date=date.today(),
        )
        assert tx.id is not None
        assert tx.amount_cents == 50000
        assert tx.type == "expense"
        assert tx.note == ""  # default

    def test_transaction_default_date(self, user, groceries):
        tx = Transaction.create(
            user=user, type="expense",
            amount_cents=10000,
            category=groceries,
        )
        assert tx.date == date.today()

    def test_transaction_with_note(self, user, groceries):
        tx = Transaction.create(
            user=user, type="expense",
            amount_cents=10000,
            category=groceries,
            note="Weekly shopping",
        )
        assert tx.note == "Weekly shopping"

    def test_transaction_without_category(self, user):
        tx = Transaction.create(
            user=user, type="expense",
            amount_cents=10000,
        )
        assert tx.category_id is None


class TestGoalModel:

    def test_create_goal(self, user):
        goal = Goal.create(
            user=user, name="Japan Trip",
            target_cents=200000,
        )
        assert goal.id is not None
        assert goal.current_cents == 0  # default
        assert goal.status == "active"  # default

    def test_goal_with_deadline(self, user):
        deadline = date(2025, 12, 31)
        goal = Goal.create(
            user=user, name="New Mac",
            target_cents=300000,
            deadline=deadline,
        )
        assert goal.deadline == deadline

    def test_goal_completion(self, user):
        from db.database import db
        goal = Goal.create(user=user, name="Test", target_cents=10000)
        with db:
            goal.current_cents = 10000
            goal.status = "completed"
            goal.save()
        assert Goal.get_by_id(goal.id).status == "completed"


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION SERVICE TESTS
# ─────────────────────────────────────────────────────────────────────────────

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
        assert tx.amount_cents == 200000

    def test_add_transaction_with_note(self, user, groceries):
        from services.transaction_service import add_transaction
        tx = add_transaction(user, "expense", 10000, category=groceries, note="  Weekly  ")
        assert tx.note == "Weekly"  # note is stripped

    def test_add_transaction_with_date(self, user, groceries):
        from services.transaction_service import add_transaction
        d = date(2025, 1, 15)
        tx = add_transaction(user, "expense", 10000, category=groceries, tx_date=d)
        assert tx.date == d

    def test_add_transaction_default_date_is_today(self, user, groceries):
        from services.transaction_service import add_transaction
        tx = add_transaction(user, "expense", 10000, category=groceries)
        assert tx.date == date.today()

    def test_zero_amount_raises(self, user):
        from services.transaction_service import add_transaction
        with pytest.raises(ValueError, match="greater than zero"):
            add_transaction(user, "expense", 0)

    def test_negative_amount_raises(self, user):
        from services.transaction_service import add_transaction
        with pytest.raises(ValueError):
            add_transaction(user, "expense", -100)

    def test_invalid_type_raises(self, user):
        from services.transaction_service import add_transaction
        with pytest.raises(ValueError, match="income.*expense"):
            add_transaction(user, "transfer", 10000)

    def test_get_all_transactions(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries)
        add_transaction(user, "expense", 20000, category=groceries)
        add_transaction(user, "income",  50000, category=salary_cat)
        txs = get_transactions(user)
        assert len(txs) == 3

    def test_get_transactions_newest_first(self, user, groceries):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 20000, category=groceries, tx_date=date(2025, 3, 15))
        txs = get_transactions(user)
        assert txs[0].amount_cents == 20000  # newer first
        assert txs[1].amount_cents == 10000

    def test_get_transactions_filter_by_type_expense(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries)
        add_transaction(user, "income",  50000, category=salary_cat)
        expenses = get_transactions(user, type="expense")
        assert len(expenses) == 1
        assert expenses[0].type == "expense"

    def test_get_transactions_filter_by_type_income(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries)
        add_transaction(user, "income",  50000, category=salary_cat)
        incomes = get_transactions(user, type="income")
        assert len(incomes) == 1
        assert incomes[0].type == "income"

    def test_get_transactions_filter_by_date_range(self, user, groceries):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries, tx_date=date(2025, 2, 15))
        add_transaction(user, "expense", 20000, category=groceries, tx_date=date(2025, 3, 10))
        add_transaction(user, "expense", 30000, category=groceries, tx_date=date(2025, 4, 5))
        march = get_transactions(user, date_from=date(2025, 3, 1), date_to=date(2025, 3, 31))
        assert len(march) == 1
        assert march[0].amount_cents == 20000

    def test_get_transactions_filter_by_category(self, user, groceries, transport):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries)
        add_transaction(user, "expense", 20000, category=transport)
        result = get_transactions(user, category=groceries)
        assert len(result) == 1
        assert result[0].category_id == groceries.id

    def test_get_transactions_limit(self, user, groceries):
        from services.transaction_service import add_transaction, get_transactions
        for i in range(10):
            add_transaction(user, "expense", 10000 * (i + 1), category=groceries)
        result = get_transactions(user, limit=3)
        assert len(result) == 3

    def test_get_transactions_isolation_between_users(self, user, user2, groceries):
        from services.transaction_service import add_transaction, get_transactions
        add_transaction(user, "expense", 10000, category=groceries)
        # user2 has no transactions
        result = get_transactions(user2)
        assert len(result) == 0

    def test_update_transaction_amount(self, user, groceries):
        from services.transaction_service import add_transaction, update_transaction
        tx = add_transaction(user, "expense", 10000, category=groceries)
        updated = update_transaction(tx, amount_cents=25000)
        assert updated.amount_cents == 25000

    def test_update_transaction_note(self, user, groceries):
        from services.transaction_service import add_transaction, update_transaction
        tx = add_transaction(user, "expense", 10000, category=groceries)
        updated = update_transaction(tx, note="New note")
        assert updated.note == "New note"

    def test_update_transaction_type(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, update_transaction
        tx = add_transaction(user, "expense", 10000, category=groceries)
        updated = update_transaction(tx, type="income")
        assert updated.type == "income"

    def test_update_transaction_invalid_amount_raises(self, user, groceries):
        from services.transaction_service import add_transaction, update_transaction
        tx = add_transaction(user, "expense", 10000, category=groceries)
        with pytest.raises(ValueError):
            update_transaction(tx, amount_cents=0)

    def test_delete_transaction(self, user, groceries):
        from services.transaction_service import add_transaction, delete_transaction, get_transactions
        tx = add_transaction(user, "expense", 10000, category=groceries)
        assert len(get_transactions(user)) == 1
        delete_transaction(tx)
        assert len(get_transactions(user)) == 0

    def test_delete_one_transaction_leaves_others(self, user, groceries):
        from services.transaction_service import add_transaction, delete_transaction, get_transactions
        tx1 = add_transaction(user, "expense", 10000, category=groceries)
        tx2 = add_transaction(user, "expense", 20000, category=groceries)
        delete_transaction(tx1)
        remaining = get_transactions(user)
        assert len(remaining) == 1
        assert remaining[0].id == tx2.id

    def test_get_totals_basic(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, get_totals
        add_transaction(user, "income",  200000, category=salary_cat)
        add_transaction(user, "expense",  80000, category=groceries)
        totals = get_totals(user)
        assert totals["income_cents"]  == 200000
        assert totals["expense_cents"] ==  80000
        assert totals["balance_cents"] == 120000

    def test_get_totals_negative_balance(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, get_totals
        add_transaction(user, "income",   50000, category=salary_cat)
        add_transaction(user, "expense", 100000, category=groceries)
        totals = get_totals(user)
        assert totals["balance_cents"] == -50000

    def test_get_totals_empty(self, user):
        from services.transaction_service import get_totals
        totals = get_totals(user)
        assert totals["income_cents"]  == 0
        assert totals["expense_cents"] == 0
        assert totals["balance_cents"] == 0

    def test_get_totals_with_date_filter(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction, get_totals
        add_transaction(user, "income",  200000, category=salary_cat, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense",  50000, category=groceries,  tx_date=date(2025, 3, 15))
        add_transaction(user, "expense",  30000, category=groceries,  tx_date=date(2025, 4, 1))
        totals = get_totals(user, date_from=date(2025, 3, 1), date_to=date(2025, 3, 31))
        assert totals["income_cents"]  == 200000
        assert totals["expense_cents"] ==  50000

    def test_get_recent_transactions(self, user, groceries):
        from services.transaction_service import add_transaction, get_recent_transactions
        for i in range(10):
            add_transaction(user, "expense", 10000 * (i + 1), category=groceries)
        recent = get_recent_transactions(user, limit=3)
        assert len(recent) == 3


# ─────────────────────────────────────────────────────────────────────────────
# BUDGET SERVICE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestBudgetService:

    def test_set_budget(self, user, groceries):
        from services.budget_service import set_budget, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2025, month=3)
        budgets = get_budgets(user, 2025, 3)
        assert len(budgets) == 1
        assert budgets[0].limit_cents == 50000

    def test_set_budget_updates_existing(self, user, groceries):
        from services.budget_service import set_budget, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2025, month=3)
        set_budget(user, groceries, limit_cents=75000, year=2025, month=3)
        budgets = get_budgets(user, 2025, 3)
        assert len(budgets) == 1  # still just one record
        assert budgets[0].limit_cents == 75000

    def test_set_budget_different_months(self, user, groceries):
        from services.budget_service import set_budget, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2025, month=3)
        set_budget(user, groceries, limit_cents=60000, year=2025, month=4)
        assert len(get_budgets(user, 2025, 3)) == 1
        assert len(get_budgets(user, 2025, 4)) == 1
        assert get_budgets(user, 2025, 3)[0].limit_cents == 50000
        assert get_budgets(user, 2025, 4)[0].limit_cents == 60000

    def test_set_budget_zero_limit_raises(self, user, groceries):
        from services.budget_service import set_budget
        with pytest.raises(ValueError):
            set_budget(user, groceries, limit_cents=0, year=2025, month=3)

    def test_set_budget_invalid_month_raises(self, user, groceries):
        from services.budget_service import set_budget
        with pytest.raises(ValueError):
            set_budget(user, groceries, limit_cents=50000, year=2025, month=13)

    def test_get_budgets_empty(self, user):
        from services.budget_service import get_budgets
        assert get_budgets(user, 2025, 3) == []

    def test_get_budgets_multiple_categories(self, user, groceries, transport):
        from services.budget_service import set_budget, get_budgets
        set_budget(user, groceries,  limit_cents=50000, year=2025, month=3)
        set_budget(user, transport, limit_cents=30000, year=2025, month=3)
        budgets = get_budgets(user, 2025, 3)
        assert len(budgets) == 2

    def test_delete_budget(self, user, groceries):
        from services.budget_service import set_budget, get_budgets, delete_budget
        b = set_budget(user, groceries, limit_cents=50000, year=2025, month=3)
        delete_budget(b)
        assert get_budgets(user, 2025, 3) == []

    def test_budget_status_ok(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        add_transaction(user, "expense", 50000, category=groceries, tx_date=date(2025, 3, 15))
        row = get_budget_status(user, 2025, 3)[0]
        assert row["spent_cents"] == 50000
        assert row["left_cents"]  == 50000
        assert row["percent"]     == 50.0
        assert row["status"]      == "ok"

    def test_budget_status_warning_at_80(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        add_transaction(user, "expense", 80000, category=groceries, tx_date=date(2025, 3, 15))
        row = get_budget_status(user, 2025, 3)[0]
        assert row["status"] == "warning"

    def test_budget_status_warning_at_99(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        add_transaction(user, "expense", 99000, category=groceries, tx_date=date(2025, 3, 15))
        assert get_budget_status(user, 2025, 3)[0]["status"] == "warning"

    def test_budget_status_danger_at_100(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        add_transaction(user, "expense", 100000, category=groceries, tx_date=date(2025, 3, 15))
        assert get_budget_status(user, 2025, 3)[0]["status"] == "danger"

    def test_budget_status_danger_over_limit(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        add_transaction(user, "expense", 150000, category=groceries, tx_date=date(2025, 3, 15))
        row = get_budget_status(user, 2025, 3)[0]
        assert row["status"]      == "danger"
        assert row["left_cents"]  == -50000  # negative = overspent
        assert row["percent"]     == 150.0

    def test_budget_status_ignores_income(self, user, groceries, salary_cat):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        # Income should NOT count against budget
        add_transaction(user, "income", 500000, category=salary_cat, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 30000, category=groceries,  tx_date=date(2025, 3, 15))
        row = get_budget_status(user, 2025, 3)[0]
        assert row["spent_cents"] == 30000

    def test_budget_status_ignores_other_months(self, user, groceries):
        from services.budget_service import set_budget, get_budget_status
        from services.transaction_service import add_transaction
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        # Transaction in April should not affect March budget
        add_transaction(user, "expense", 80000, category=groceries, tx_date=date(2025, 4, 1))
        row = get_budget_status(user, 2025, 3)[0]
        assert row["spent_cents"] == 0

    def test_copy_budgets_from_previous_month(self, user, groceries, transport):
        from services.budget_service import set_budget, copy_budgets_from_previous_month, get_budgets
        set_budget(user, groceries,  limit_cents=50000, year=2025, month=3)
        set_budget(user, transport, limit_cents=30000, year=2025, month=3)
        copied = copy_budgets_from_previous_month(user, year=2025, month=4)
        assert copied == 2
        april = get_budgets(user, 2025, 4)
        limits = {b.category_id: b.limit_cents for b in april}
        assert limits[groceries.id]  == 50000
        assert limits[transport.id] == 30000

    def test_copy_budgets_from_january_to_february(self, user, groceries):
        from services.budget_service import set_budget, copy_budgets_from_previous_month, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2025, month=1)
        copied = copy_budgets_from_previous_month(user, year=2025, month=2)
        assert copied == 1
        assert get_budgets(user, 2025, 2)[0].limit_cents == 50000

    def test_copy_budgets_from_december_to_january(self, user, groceries):
        from services.budget_service import set_budget, copy_budgets_from_previous_month, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2024, month=12)
        copied = copy_budgets_from_previous_month(user, year=2025, month=1)
        assert copied == 1

    def test_copy_budgets_empty_previous_month(self, user):
        from services.budget_service import copy_budgets_from_previous_month
        copied = copy_budgets_from_previous_month(user, year=2025, month=4)
        assert copied == 0


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS SERVICE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyticsService:

    def test_get_balance_basic(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_balance
        add_transaction(user, "income",  300000, category=salary_cat)
        add_transaction(user, "expense", 120000, category=groceries)
        b = get_balance(user)
        assert b["income_cents"]  == 300000
        assert b["expense_cents"] == 120000
        assert b["balance_cents"] == 180000

    def test_get_balance_empty(self, user):
        from services.analytics_service import get_balance
        b = get_balance(user)
        assert b["income_cents"]  == 0
        assert b["expense_cents"] == 0
        assert b["balance_cents"] == 0

    def test_get_balance_negative(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_balance
        add_transaction(user, "income",   50000, category=salary_cat)
        add_transaction(user, "expense", 100000, category=groceries)
        b = get_balance(user)
        assert b["balance_cents"] == -50000

    def test_get_balance_isolation_between_users(self, user, user2, groceries, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_balance
        add_transaction(user, "income", 300000, category=salary_cat)
        b = get_balance(user2)
        assert b["income_cents"] == 0

    def test_get_spending_by_category_basic(self, user, groceries):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_spending_by_category
        add_transaction(user, "expense", 30000, category=groceries, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 20000, category=groceries, tx_date=date(2025, 3, 15))
        result = get_spending_by_category(user, date(2025, 3, 1), date(2025, 3, 31))
        assert len(result) == 1
        assert result[0]["spent_cents"] == 50000
        assert result[0]["percent"]     == 100.0

    def test_get_spending_by_category_multiple(self, user, groceries, transport):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_spending_by_category
        add_transaction(user, "expense", 60000, category=groceries,  tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 40000, category=transport, tx_date=date(2025, 3, 2))
        result = get_spending_by_category(user, date(2025, 3, 1), date(2025, 3, 31))
        assert len(result) == 2
        # Sorted largest first
        assert result[0]["spent_cents"] == 60000
        assert result[1]["spent_cents"] == 40000
        assert result[0]["percent"] == 60.0
        assert result[1]["percent"] == 40.0

    def test_get_spending_by_category_ignores_income(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_spending_by_category
        add_transaction(user, "income",  200000, category=salary_cat, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense",  50000, category=groceries,  tx_date=date(2025, 3, 15))
        result = get_spending_by_category(user, date(2025, 3, 1), date(2025, 3, 31))
        # Only expense categories should appear
        assert len(result) == 1
        assert result[0]["spent_cents"] == 50000

    def test_get_spending_by_category_empty(self, user):
        from services.analytics_service import get_spending_by_category
        result = get_spending_by_category(user, date(2025, 3, 1), date(2025, 3, 31))
        assert result == []

    def test_get_spending_by_category_sorted_largest_first(self, user, groceries, transport):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_spending_by_category
        add_transaction(user, "expense", 10000, category=groceries,  tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 90000, category=transport, tx_date=date(2025, 3, 2))
        result = get_spending_by_category(user, date(2025, 3, 1), date(2025, 3, 31))
        assert result[0]["spent_cents"] == 90000  # transport is largest

    def test_get_daily_totals_basic(self, user, groceries):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_daily_totals
        add_transaction(user, "expense", 10000, category=groceries, tx_date=date(2025, 3, 1))
        result = get_daily_totals(user, date(2025, 3, 1), date(2025, 3, 3))
        assert len(result) == 3
        assert result[0]["amount_cents"] == 10000
        assert result[1]["amount_cents"] == 0
        assert result[2]["amount_cents"] == 0

    def test_get_daily_totals_fills_all_days(self, user, groceries):
        from services.analytics_service import get_daily_totals
        # No transactions — all days should be 0
        result = get_daily_totals(user, date(2025, 3, 1), date(2025, 3, 31))
        assert len(result) == 31
        assert all(d["amount_cents"] == 0 for d in result)

    def test_get_daily_totals_multiple_on_same_day(self, user, groceries):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_daily_totals
        add_transaction(user, "expense", 10000, category=groceries, tx_date=date(2025, 3, 5))
        add_transaction(user, "expense", 20000, category=groceries, tx_date=date(2025, 3, 5))
        result = get_daily_totals(user, date(2025, 3, 5), date(2025, 3, 5))
        assert result[0]["amount_cents"] == 30000  # summed correctly

    def test_get_daily_totals_income_type(self, user, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_daily_totals
        add_transaction(user, "income", 200000, category=salary_cat, tx_date=date(2025, 3, 1))
        result = get_daily_totals(user, date(2025, 3, 1), date(2025, 3, 1), type="income")
        assert result[0]["amount_cents"] == 200000

    def test_get_monthly_totals(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_monthly_totals
        add_transaction(user, "income",  200000, category=salary_cat, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense",  80000, category=groceries,  tx_date=date(2025, 3, 15))
        add_transaction(user, "expense",  50000, category=groceries,  tx_date=date(2025, 5, 10))
        result = get_monthly_totals(user, 2025)
        assert len(result) == 12  # all 12 months
        march = next(r for r in result if r["month"] == 3)
        may   = next(r for r in result if r["month"] == 5)
        assert march["income_cents"]  == 200000
        assert march["expense_cents"] ==  80000
        assert may["expense_cents"]   ==  50000

    def test_get_top_categories(self, user, groceries, transport, freelance_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_top_categories
        add_transaction(user, "expense", 90000, category=groceries,  tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 50000, category=transport, tx_date=date(2025, 3, 2))
        result = get_top_categories(user, date(2025, 3, 1), date(2025, 3, 31), top_n=1)
        assert len(result) == 1
        assert result[0]["spent_cents"] == 90000  # groceries is top

    def test_get_month_summary_basic(self, user, groceries, salary_cat):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_month_summary
        add_transaction(user, "income",  200000, category=salary_cat, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense",  80000, category=groceries,  tx_date=date(2025, 3, 10))
        summary = get_month_summary(user, 2025, 3)
        assert summary["income_cents"]  == 200000
        assert summary["expense_cents"] ==  80000
        assert summary["balance_cents"] == 120000

    def test_get_month_summary_has_required_keys(self, user):
        from services.analytics_service import get_month_summary
        summary = get_month_summary(user, 2025, 3)
        assert "income_cents"    in summary
        assert "expense_cents"   in summary
        assert "balance_cents"   in summary
        assert "top_categories"  in summary
        assert "days_left"       in summary
        assert "daily_avg_cents" in summary

    def test_get_month_summary_empty(self, user):
        from services.analytics_service import get_month_summary
        summary = get_month_summary(user, 2025, 3)
        assert summary["income_cents"]  == 0
        assert summary["expense_cents"] == 0
        assert summary["balance_cents"] == 0
        assert summary["top_categories"] == []

    def test_get_month_summary_daily_avg(self, user, groceries):
        from services.transaction_service import add_transaction
        from services.analytics_service import get_month_summary
        # 31000 spent on March 1st
        add_transaction(user, "expense", 31000, category=groceries, tx_date=date(2025, 3, 1))
        summary = get_month_summary(user, 2025, 3)
        # daily avg = 31000 / days_passed
        assert summary["daily_avg_cents"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTER TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatters:

    def setup_method(self):
        from utils.formatters import set_currency
        set_currency("USD")

    def test_format_money_basic(self):
        from utils.formatters import format_money
        result = format_money(150000)
        assert "1 500" in result
        assert "$" in result

    def test_format_money_with_cents(self):
        from utils.formatters import format_money
        assert "1 500.50" in format_money(150050)

    def test_format_money_zero(self):
        from utils.formatters import format_money
        assert "0.00" in format_money(0)

    def test_format_money_negative(self):
        from utils.formatters import format_money
        result = format_money(-50000)
        assert "-" in result
        assert "500" in result

    def test_format_money_show_sign_positive(self):
        from utils.formatters import format_money
        assert "+" in format_money(100, show_sign=True)

    def test_format_money_show_sign_negative(self):
        from utils.formatters import format_money
        result = format_money(-100, show_sign=True)
        assert "+" not in result
        assert "-" in result

    def test_format_money_rub(self):
        from utils.formatters import format_money, set_currency
        set_currency("RUB")
        assert "₽" in format_money(100000)

    def test_format_money_eur(self):
        from utils.formatters import format_money, set_currency
        set_currency("EUR")
        assert "€" in format_money(100000)

    def test_format_money_ils(self):
        from utils.formatters import format_money, set_currency
        set_currency("ILS")
        assert "₪" in format_money(100000)

    def test_format_money_short_whole_number(self):
        from utils.formatters import format_money_short
        result = format_money_short(150000)
        assert "1 500" in result
        assert "." not in result  # no decimals for whole numbers

    def test_format_money_short_with_cents(self):
        from utils.formatters import format_money_short
        result = format_money_short(150050)
        assert "1 500" in result

    def test_parse_money_integer(self):
        from utils.formatters import parse_money
        assert parse_money("1500") == 150000

    def test_parse_money_decimal_dot(self):
        from utils.formatters import parse_money
        assert parse_money("1500.50") == 150050

    def test_parse_money_decimal_comma(self):
        from utils.formatters import parse_money
        assert parse_money("1500,50") == 150050

    def test_parse_money_with_spaces(self):
        from utils.formatters import parse_money
        assert parse_money("1 500") == 150000

    def test_parse_money_small_amount(self):
        from utils.formatters import parse_money
        assert parse_money("0.01") == 1

    def test_parse_money_large_amount(self):
        from utils.formatters import parse_money
        assert parse_money("1000000") == 100000000

    def test_parse_money_invalid_raises(self):
        from utils.formatters import parse_money
        with pytest.raises(ValueError):
            parse_money("abc")

    def test_parse_money_empty_raises(self):
        from utils.formatters import parse_money
        with pytest.raises(ValueError):
            parse_money("")

    def test_parse_money_roundtrip(self):
        from utils.formatters import parse_money
        for original in [100, 999, 12345, 99999]:
            parsed = parse_money(str(original / 100))
            assert parsed == original

    def test_format_date(self):
        from utils.formatters import format_date
        assert format_date(date(2025, 3, 19)) == "19.03.2025"

    def test_format_date_short_march(self):
        from utils.formatters import format_date_short
        assert format_date_short(date(2025, 3, 19)) == "19 Mar"

    def test_format_date_short_january(self):
        from utils.formatters import format_date_short
        assert format_date_short(date(2025, 1, 1)) == "1 Jan"

    def test_format_date_short_december(self):
        from utils.formatters import format_date_short
        assert format_date_short(date(2025, 12, 31)) == "31 Dec"

    def test_parse_date_valid(self):
        from utils.formatters import parse_date
        assert parse_date("19.03.2025") == date(2025, 3, 19)

    def test_parse_date_invalid_raises(self):
        from utils.formatters import parse_date
        with pytest.raises(ValueError):
            parse_date("2025-03-19")  # wrong format

    def test_month_name(self):
        from utils.formatters import month_name
        assert month_name(1,  2025) == "January 2025"
        assert month_name(12, 2025) == "December 2025"
        assert month_name(6,  2024) == "June 2024"

    def test_percent_basic(self):
        from utils.formatters import percent
        assert percent(50, 100) == 50.0

    def test_percent_zero_total(self):
        from utils.formatters import percent
        assert percent(100, 0) == 0.0

    def test_percent_over_100(self):
        from utils.formatters import percent
        assert percent(150, 100) == 150.0

    def test_percent_zero_part(self):
        from utils.formatters import percent
        assert percent(0, 100) == 0.0

    def test_percent_exact_100(self):
        from utils.formatters import percent
        assert percent(100, 100) == 100.0


# ─────────────────────────────────────────────────────────────────────────────
# EDGE CASE & INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_money_stored_as_cents_not_float(self, user, groceries):
        """Critical: ensure no floating point errors in money calculations."""
        from services.transaction_service import add_transaction, get_totals
        # 0.1 + 0.2 = 0.30000000000000004 in float — should be exactly 30 cents
        add_transaction(user, "expense", 10, category=groceries)  # 0.10
        add_transaction(user, "expense", 20, category=groceries)  # 0.20
        totals = get_totals(user)
        assert totals["expense_cents"] == 30  # exactly 30 cents

    def test_large_amounts(self, user, salary_cat):
        """Test with realistically large amounts."""
        from services.transaction_service import add_transaction, get_totals
        # 1,000,000.00 salary
        add_transaction(user, "income", 100000000, category=salary_cat)
        totals = get_totals(user)
        assert totals["income_cents"] == 100000000

    def test_transaction_isolation_between_users(self, user, user2, groceries):
        """User 2 should never see User 1's transactions."""
        from services.transaction_service import add_transaction, get_transactions, get_totals
        add_transaction(user, "expense", 50000, category=groceries)
        assert get_transactions(user2) == []
        assert get_totals(user2)["expense_cents"] == 0

    def test_budget_isolation_between_users(self, user, user2, groceries):
        """User 2 should never see User 1's budgets."""
        from services.budget_service import set_budget, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2025, month=3)
        assert get_budgets(user2, 2025, 3) == []

    def test_december_to_january_budget_copy(self, user, groceries):
        """Edge case: copying budget from December to January crosses year boundary."""
        from services.budget_service import set_budget, copy_budgets_from_previous_month, get_budgets
        set_budget(user, groceries, limit_cents=50000, year=2024, month=12)
        copy_budgets_from_previous_month(user, year=2025, month=1)
        jan_budgets = get_budgets(user, 2025, 1)
        assert len(jan_budgets) == 1
        assert jan_budgets[0].limit_cents == 50000

    def test_analytics_period_boundary(self, user, groceries):
        """Transactions exactly on period boundaries should be included."""
        from services.transaction_service import add_transaction
        from services.analytics_service import get_spending_by_category
        # First and last day of March
        add_transaction(user, "expense", 10000, category=groceries, tx_date=date(2025, 3, 1))
        add_transaction(user, "expense", 20000, category=groceries, tx_date=date(2025, 3, 31))
        result = get_spending_by_category(user, date(2025, 3, 1), date(2025, 3, 31))
        assert result[0]["spent_cents"] == 30000  # both included

    def test_goal_contribute_marks_completed(self, user):
        """Goal should auto-complete when current reaches target."""
        from db.database import db
        goal = Goal.create(user=user, name="Test", target_cents=10000)
        from db.database import db as _db
        def contribute_to_goal(goal, amount_cents):
            with _db:
                goal.current_cents += amount_cents
                if goal.current_cents >= goal.target_cents:
                    goal.status = "completed"
                goal.save()
        contribute_to_goal(goal, 10000)
        updated = Goal.get_by_id(goal.id)
        assert updated.status == "completed"

    def test_goal_contribute_does_not_exceed_target_in_status(self, user):
        """Contributing more than target still marks as completed, not broken."""
        from db.database import db as _db
        def contribute_to_goal(goal, amount_cents):
            with _db:
                goal.current_cents += amount_cents
                if goal.current_cents >= goal.target_cents:
                    goal.status = "completed"
                goal.save()
        goal = Goal.create(user=user, name="Test", target_cents=10000)
        contribute_to_goal(goal, 15000)  # 150% of target
        assert Goal.get_by_id(goal.id).status == "completed"

    def test_multiple_transactions_same_day_daily_totals(self, user, groceries):
        """Multiple transactions on the same day should be summed."""
        from services.transaction_service import add_transaction
        from services.analytics_service import get_daily_totals
        for amount in [10000, 20000, 30000]:
            add_transaction(user, "expense", amount, category=groceries, tx_date=date(2025, 3, 15))
        result = get_daily_totals(user, date(2025, 3, 15), date(2025, 3, 15))
        assert result[0]["amount_cents"] == 60000

    def test_budget_with_no_transactions_shows_zero_spent(self, user, groceries):
        """Budget with no transactions should show 0 spent and full limit remaining."""
        from services.budget_service import set_budget, get_budget_status
        set_budget(user, groceries, limit_cents=100000, year=2025, month=3)
        row = get_budget_status(user, 2025, 3)[0]
        assert row["spent_cents"] == 0
        assert row["left_cents"]  == 100000
        assert row["percent"]     == 0.0
        assert row["status"]      == "ok"




# ─────────────────────────────────────────────────────────────────────────────
# GOAL SERVICE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestGoalService:

    def test_add_goal_basic(self, user):
        from services.goal_service import add_goal, get_goals
        goal = add_goal(user, "Japan Trip", 200000)
        assert goal.id is not None
        assert goal.name == "Japan Trip"
        assert goal.target_cents == 200000
        assert goal.current_cents == 0
        assert goal.status == "active"
        assert goal.icon == "🎯"

    def test_add_goal_empty_name_raises(self, user):
        from services.goal_service import add_goal
        with pytest.raises(ValueError, match="empty"):
            add_goal(user, "", 200000)

    def test_add_goal_zero_amount_raises(self, user):
        from services.goal_service import add_goal
        with pytest.raises(ValueError, match="greater than zero"):
            add_goal(user, "Test", 0)

    def test_add_goal_negative_amount_raises(self, user):
        from services.goal_service import add_goal
        with pytest.raises(ValueError):
            add_goal(user, "Test", -100)

    def test_add_goal_with_deadline(self, user):
        from services.goal_service import add_goal
        from datetime import date
        deadline = date(2026, 6, 1)
        goal = add_goal(user, "Vacation", 100000, deadline=deadline)
        assert goal.deadline == deadline

    def test_add_goal_custom_icon(self, user):
        from services.goal_service import add_goal
        goal = add_goal(user, "Car", 500000, icon="🚗")
        assert goal.icon == "🚗"

    def test_get_goals_returns_active(self, user):
        from services.goal_service import add_goal, get_goals
        add_goal(user, "Goal 1", 100000)
        add_goal(user, "Goal 2", 200000)
        goals = get_goals(user)
        assert len(goals) == 2

    def test_get_goals_newest_first(self, user):
        from services.goal_service import add_goal, get_goals
        add_goal(user, "First", 100000)
        add_goal(user, "Second", 200000)
        goals = get_goals(user)
        assert goals[0].name == "Second"

    def test_get_goals_excludes_archived(self, user):
        from services.goal_service import add_goal, get_goals, archive_goal
        g = add_goal(user, "Goal", 100000)
        archive_goal(g)
        goals = get_goals(user)
        assert len(goals) == 0

    def test_get_goals_includes_completed(self, user):
        from services.goal_service import add_goal, get_goals, contribute_to_goal
        g = add_goal(user, "Goal", 10000)
        contribute_to_goal(g, 10000)
        goals = get_goals(user)
        assert len(goals) == 1
        assert goals[0].status == "completed"

    def test_contribute_basic(self, user):
        from services.goal_service import add_goal, contribute_to_goal
        goal = add_goal(user, "Test", 10000)
        contribute_to_goal(goal, 3000)
        assert goal.current_cents == 3000
        assert goal.status == "active"

    def test_contribute_marks_completed(self, user):
        from services.goal_service import add_goal, contribute_to_goal
        goal = add_goal(user, "Test", 10000)
        contribute_to_goal(goal, 10000)
        assert goal.status == "completed"

    def test_contribute_over_target_marks_completed(self, user):
        from services.goal_service import add_goal, contribute_to_goal
        goal = add_goal(user, "Test", 10000)
        contribute_to_goal(goal, 15000)
        assert goal.status == "completed"
        assert goal.current_cents == 15000

    def test_contribute_zero_raises(self, user):
        from services.goal_service import add_goal, contribute_to_goal
        goal = add_goal(user, "Test", 10000)
        with pytest.raises(ValueError):
            contribute_to_goal(goal, 0)

    def test_contribute_negative_raises(self, user):
        from services.goal_service import add_goal, contribute_to_goal
        goal = add_goal(user, "Test", 10000)
        with pytest.raises(ValueError):
            contribute_to_goal(goal, -100)

    def test_archive_goal(self, user):
        from services.goal_service import add_goal, archive_goal
        goal = add_goal(user, "Test", 10000)
        archive_goal(goal)
        assert goal.status == "archived"

    def test_get_goal_progress_empty(self, user):
        from services.goal_service import add_goal, get_goal_progress
        goal = add_goal(user, "Test", 10000)
        progress = get_goal_progress(goal)
        assert progress["percent"] == 0.0
        assert progress["remaining_cents"] == 10000
        assert progress["is_completed"] == False

    def test_get_goal_progress_half(self, user):
        from services.goal_service import add_goal, contribute_to_goal, get_goal_progress
        goal = add_goal(user, "Test", 10000)
        contribute_to_goal(goal, 5000)
        progress = get_goal_progress(goal)
        assert progress["percent"] == 50.0
        assert progress["remaining_cents"] == 5000
        assert progress["is_completed"] == False

    def test_get_goal_progress_completed(self, user):
        from services.goal_service import add_goal, contribute_to_goal, get_goal_progress
        goal = add_goal(user, "Test", 10000)
        contribute_to_goal(goal, 10000)
        progress = get_goal_progress(goal)
        assert progress["percent"] == 100.0
        assert progress["remaining_cents"] == 0
        assert progress["is_completed"] == True

    def test_get_goal_deadline_info_no_deadline(self, user):
        from services.goal_service import add_goal, get_goal_deadline_info
        goal = add_goal(user, "Test", 10000)
        info = get_goal_deadline_info(goal)
        assert info["has_deadline"] == False
        assert info["days_left"] is None
        assert info["needed_per_month"] is None

    def test_get_goal_deadline_info_future(self, user):
        from services.goal_service import add_goal, get_goal_deadline_info
        from datetime import date, timedelta
        future = date.today() + timedelta(days=60)
        goal = add_goal(user, "Test", 120000, deadline=future)
        info = get_goal_deadline_info(goal)
        assert info["has_deadline"] == True
        assert info["days_left"] > 0
        assert info["is_overdue"] == False
        assert info["needed_per_month"] > 0

    def test_get_goal_deadline_info_overdue(self, user):
        from services.goal_service import add_goal, get_goal_deadline_info
        from datetime import date, timedelta
        past = date.today() - timedelta(days=10)
        goal = add_goal(user, "Test", 10000, deadline=past)
        info = get_goal_deadline_info(goal)
        assert info["has_deadline"] == True
        assert info["is_overdue"] == True
        assert info["days_left"] < 0

    def test_goal_isolation_between_users(self, user, user2):
        from services.goal_service import add_goal, get_goals
        add_goal(user, "User1 Goal", 10000)
        goals_user2 = get_goals(user2)
        assert len(goals_user2) == 0