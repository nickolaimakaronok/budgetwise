"""
tests/test_row_limit.py
No silent row limit: lists, totals, exports and search cover ALL transactions.
(Before: get_transactions() returned at most 200 rows by default.)
Run with: python -m pytest tests/test_row_limit.py -v
"""

from datetime import date

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, User, Category
from services.transaction_service import (
    add_transaction, get_transactions, get_recent_transactions,
    get_totals, filter_transactions,
)
from services.tag_service import set_transaction_tags, get_or_create_tag

test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def setup_db():
    test_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(ALL_MODELS)
    yield
    test_db.drop_tables(ALL_MODELS)
    test_db.close()


@pytest.fixture
def user():
    return User.create(name="Test User", currency="ILS")


@pytest.fixture
def rent(user):
    return Category.create(user=user, name="Rent", type="expense")


@pytest.fixture
def groceries():
    return Category.create(user=None, name="Продукты", icon="🛒", type="expense")


@pytest.fixture
def salary():
    return Category.create(user=None, name="Salary", type="income")


def _add_many(user, cat, n=250):
    for i in range(n):
        add_transaction(user, "expense", 100, cat, date(2026, 3, 1 + i % 28))


def test_get_transactions_returns_everything(user, rent):
    _add_many(user, rent)
    assert len(get_transactions(user)) == 250


def test_get_totals_counts_everything(user, rent, salary):
    _add_many(user, rent)
    add_transaction(user, "income", 99999, salary, date(2026, 3, 2))
    totals = get_totals(user)
    assert totals["expense_cents"] == 25000          # was 20000 with the 200-row cap
    assert totals["income_cents"] == 99999
    assert totals["balance_cents"] == 99999 - 25000


def test_get_totals_date_range(user, rent):
    add_transaction(user, "expense", 100, rent, date(2026, 2, 28))
    add_transaction(user, "expense", 200, rent, date(2026, 3, 1))
    add_transaction(user, "expense", 400, rent, date(2026, 4, 1))
    t = get_totals(user, date_from=date(2026, 3, 1), date_to=date(2026, 3, 31))
    assert t["expense_cents"] == 200


def test_get_totals_empty(user):
    assert get_totals(user) == {"income_cents": 0, "expense_cents": 0, "balance_cents": 0}


def test_explicit_limit_still_works(user, rent):
    _add_many(user, rent, 10)
    assert len(get_recent_transactions(user, limit=5)) == 5


def test_transactions_without_category_are_kept(user, rent):
    add_transaction(user, "expense", 100, rent)
    add_transaction(user, "expense", 200, None)
    assert len(get_transactions(user)) == 2


def test_filter_covers_all_rows(user, rent):
    _add_many(user, rent)
    assert len(filter_transactions(user, search="rent")) == 250


def test_search_cyrillic_case_insensitive(user, groceries, rent):
    add_transaction(user, "expense", 100, groceries, note="Магазин")
    add_transaction(user, "expense", 100, rent)
    assert len(filter_transactions(user, search="продукты")) == 1
    assert len(filter_transactions(user, search="МАГАЗИН")) == 1


def test_search_and_filter_by_tag(user, rent):
    a = add_transaction(user, "expense", 100, rent, note="flat")
    add_transaction(user, "expense", 100, rent, note="other")
    set_transaction_tags(a, user, ["vacation", "work"])
    result = filter_transactions(user, search="#vacat")
    assert [tx.id for tx in result] == [a.id]
    assert result[0].tag_names == ["vacation", "work"]
    vacation = get_or_create_tag(user, "vacation")
    assert [tx.id for tx in filter_transactions(user, tag=vacation)] == [a.id]