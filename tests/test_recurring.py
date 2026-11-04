"""
tests/test_recurring.py
Recurring series: one template + linked monthly copies.
Each test reproduces a bug of the old logic (every copy was a template too).
Run with: python -m pytest tests/test_recurring.py -v
"""

from datetime import date

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, User, Category, Transaction
from services.transaction_service import (
    add_transaction, update_transaction, delete_transaction,
    create_recurring_for_month, get_recurring_transactions,
    set_recurring, is_series_active,
)

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


def _template(user, cat, d, amount=500000, note="rent"):
    return add_transaction(user, "expense", amount, cat, d, note, is_recurring=True)


def _dates():
    return [tx.date for tx in Transaction.select().order_by(Transaction.date, Transaction.id)]


def test_copies_are_not_templates(user, rent):
    tpl = _template(user, rent, date(2026, 1, 15))
    for m in (2, 3, 4):
        create_recurring_for_month(user, 2026, m)
    assert [t.id for t in get_recurring_transactions(user)] == [tpl.id]
    copies = list(Transaction.select().where(Transaction.recurring_parent == tpl.id))
    assert len(copies) == 3
    assert all(not c.is_recurring for c in copies)


def test_day_does_not_drift(user, rent):
    _template(user, rent, date(2026, 1, 30))
    for m in (2, 3, 4):
        create_recurring_for_month(user, 2026, m)
    assert _dates() == [date(2026, 1, 30), date(2026, 2, 28), date(2026, 3, 30), date(2026, 4, 30)]


def test_last_day_stays_last_day(user, rent):
    _template(user, rent, date(2026, 1, 31))
    create_recurring_for_month(user, 2026, 4)
    assert _dates() == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]


def test_idempotent(user, rent):
    _template(user, rent, date(2026, 1, 15))
    assert create_recurring_for_month(user, 2026, 3) == 2
    assert create_recurring_for_month(user, 2026, 3) == 0
    assert create_recurring_for_month(user, 2026, 2) == 0
    assert Transaction.select().count() == 3


def test_template_month_gets_no_copy(user, rent):
    _template(user, rent, date(2026, 3, 15))
    assert create_recurring_for_month(user, 2026, 3) == 0
    assert Transaction.select().count() == 1


def test_missed_months_are_caught_up(user, rent):
    _template(user, rent, date(2026, 1, 10))
    assert create_recurring_for_month(user, 2026, 5) == 4      # Feb..May
    assert _dates()[-1] == date(2026, 5, 10)


def test_deleted_copy_is_not_recreated(user, rent):
    _template(user, rent, date(2026, 1, 10))
    create_recurring_for_month(user, 2026, 3)
    delete_transaction(Transaction.get(Transaction.date == date(2026, 3, 10)))
    assert create_recurring_for_month(user, 2026, 3) == 0
    assert date(2026, 3, 10) not in _dates()


def test_price_change_on_a_copy_gives_no_double_charge(user, rent):
    """Old code: editing one copy's amount made the next month get TWO copies."""
    _template(user, rent, date(2026, 8, 3), amount=5000, note="YouTube Premium")
    create_recurring_for_month(user, 2026, 11)
    nov = Transaction.get(Transaction.date == date(2026, 11, 3))
    update_transaction(nov, amount_cents=5500)
    create_recurring_for_month(user, 2026, 12)
    december = Transaction.select().where(Transaction.date >= date(2026, 12, 1))
    assert december.count() == 1


def test_stop_series_from_a_copy(user, rent):
    tpl = _template(user, rent, date(2026, 1, 10))
    create_recurring_for_month(user, 2026, 2)
    copy = Transaction.get(Transaction.recurring_parent == tpl.id)
    assert is_series_active(copy)
    set_recurring(copy, False)
    assert not is_series_active(copy)
    assert create_recurring_for_month(user, 2026, 6) == 0


def test_restart_series_does_not_backfill(user, rent):
    tpl = _template(user, rent, date(2026, 1, 10))
    create_recurring_for_month(user, 2026, 2)
    set_recurring(tpl, False)
    set_recurring(tpl, True, today=date(2026, 6, 5))        # back on in June
    assert create_recurring_for_month(user, 2026, 6) == 1   # only June, not Mar–May
    assert _dates()[-1] == date(2026, 6, 10)


def test_enable_on_plain_transaction(user, rent):
    tx = add_transaction(user, "expense", 1000, rent, date(2026, 6, 3), "gym")
    set_recurring(tx, True, today=date(2026, 6, 20))
    assert create_recurring_for_month(user, 2026, 6) == 0
    assert create_recurring_for_month(user, 2026, 7) == 1


def test_deleting_template_keeps_series_alive(user, rent):
    tpl = _template(user, rent, date(2026, 1, 10))
    create_recurring_for_month(user, 2026, 3)
    delete_transaction(tpl)
    templates = get_recurring_transactions(user)
    assert len(templates) == 1
    heir = templates[0]
    assert heir.date == date(2026, 3, 10)
    assert Transaction.select().where(Transaction.recurring_parent == heir.id).count() == 1
    assert create_recurring_for_month(user, 2026, 4) == 1
    assert create_recurring_for_month(user, 2026, 4) == 0


def test_editing_stale_template_keeps_bookkeeping(user, rent):
    """The Edit dialog holds an object loaded before generation ran."""
    stale = _template(user, rent, date(2026, 1, 10))
    create_recurring_for_month(user, 2026, 3)
    update_transaction(stale, amount_cents=600000)
    assert create_recurring_for_month(user, 2026, 3) == 0
    assert Transaction.get_by_id(stale.id).amount_cents == 600000