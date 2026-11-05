"""
tests/test_currency_change.py
Changing the main currency: "only the symbol" vs "convert everything",
exact amounts for purchases made in the new currency, cross-rates,
a round trip back, and all-or-nothing when something fails half way.
"""

from datetime import date
from decimal import Decimal

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, Budget, Category, ExchangeRate, Goal, Transaction, User
from services.currency_service import (
    MODE_CONVERT, MODE_RELABEL, add_transaction_in_currency, change_main_currency,
    get_rate, set_rate,
)
from services.transaction_service import get_totals

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
    """Lives in Israel (₪), has a coffee in shekels, one in euro, one in dollars, a budget and a goal."""
    u = User.create(name="Nick", currency="ILS")
    cafe = Category.create(user=None, name="Cafe", icon="☕", type="expense")
    set_rate(u, "EUR", "3.95")
    set_rate(u, "USD", "3.70")
    day = date(2026, 11, 5)
    add_transaction_in_currency(u, "expense", 7000, category=cafe, tx_date=day, note="shekels")
    add_transaction_in_currency(u, "expense", 2000, "EUR", category=cafe, tx_date=day, note="euro")
    add_transaction_in_currency(u, "expense", 1000, "USD", category=cafe, tx_date=day, note="dollars")
    Budget.create(user=u, category=cafe, period_year=2026, period_month=11, limit_cents=10000)
    Goal.create(user=u, name="Trip", target_cents=395000, current_cents=39500)
    return u


def _tx(note):
    return Transaction.get(Transaction.note == note)


def _fresh(user):
    return User.get_by_id(user.id)


# ── Only the symbol ───────────────────────────────────────────────────────────

def test_relabel_keeps_every_number(user):
    change_main_currency(user, "EUR", MODE_RELABEL)
    assert _fresh(user).currency == "EUR"
    assert _tx("shekels").amount_cents == 7000
    assert Budget.get().limit_cents == 10000
    assert get_rate(user, "EUR") is None                      # the main currency needs no rate
    assert get_rate(user, "USD") == Decimal("3.70")           # other rates untouched


# ── Convert everything ────────────────────────────────────────────────────────

def test_convert_shekel_purchase_remembers_where_it_came_from(user):
    change_main_currency(user, "EUR", MODE_CONVERT, rate="3.95")
    tx = _tx("shekels")
    assert tx.amount_cents == 1772                            # 70 / 3.95 = 17.72
    assert (tx.currency, tx.original_amount_cents, tx.exchange_rate) == ("ILS", 7000, "0.25316456")


def test_convert_euro_purchase_gets_its_exact_amount_back(user):
    change_main_currency(user, "EUR", MODE_CONVERT, rate="3.95")
    tx = _tx("euro")
    assert tx.amount_cents == 2000                            # exactly 20.00 €, not 79 / 3.95
    assert tx.currency is None and not tx.is_foreign


def test_convert_third_currency_uses_cross_rate(user):
    change_main_currency(user, "EUR", MODE_CONVERT, rate="3.95")
    tx = _tx("dollars")
    assert tx.amount_cents == 937                             # 37.00 ₪ / 3.95 = 9.37 €
    assert (tx.currency, tx.original_amount_cents) == ("USD", 1000)
    assert tx.exchange_rate == "0.93670886"                   # 1 USD = 3.70 ₪ = 0.9367 €


def test_convert_budgets_goals_and_rates(user):
    counts = change_main_currency(user, "EUR", MODE_CONVERT, rate="3.95")
    assert counts == {"transactions": 3, "budgets": 1, "goals": 1}
    assert Budget.get().limit_cents == 2532                   # 100 ₪ → 25.32 €
    goal = Goal.get()
    assert (goal.target_cents, goal.current_cents) == (100000, 10000)
    assert get_rate(user, "EUR") is None
    assert get_rate(user, "USD") == Decimal("0.93670886")
    assert get_rate(user, "ILS") == Decimal("0.25316456")     # can still enter purchases in ₪
    assert _fresh(user).currency == "EUR"


def test_totals_are_in_the_new_currency(user):
    change_main_currency(user, "EUR", MODE_CONVERT, rate="3.95")
    assert get_totals(user)["expense_cents"] == 1772 + 2000 + 937


def test_round_trip_gives_shekels_back_exactly(user):
    change_main_currency(user, "EUR", MODE_CONVERT, rate="3.95")
    change_main_currency(user, "ILS", MODE_CONVERT, rate=get_rate(user, "ILS"))
    tx = _tx("shekels")
    assert tx.amount_cents == 7000 and tx.currency is None
    euro = _tx("euro")
    assert (euro.currency, euro.original_amount_cents, euro.amount_cents) == ("EUR", 2000, 7900)


# ── Safety ────────────────────────────────────────────────────────────────────

def test_wrong_input_is_rejected(user):
    with pytest.raises(ValueError):
        change_main_currency(user, "ILS", MODE_CONVERT, rate="1")     # already the main one
    with pytest.raises(ValueError):
        change_main_currency(user, "EUR", MODE_CONVERT)                # convert needs a rate
    with pytest.raises(ValueError):
        change_main_currency(user, "EUR", "something else", rate="3.95")


def test_all_or_nothing(user, monkeypatch):
    """If anything fails half way, not a single amount is changed."""
    def broken_save(self, *args, **kwargs):
        raise RuntimeError("disk full")
    monkeypatch.setattr(Goal, "save", broken_save)            # goals come after transactions

    with pytest.raises(RuntimeError):
        change_main_currency(user, "EUR", MODE_CONVERT, rate="3.95")

    assert _tx("shekels").amount_cents == 7000
    assert _tx("shekels").currency is None
    assert Budget.get().limit_cents == 10000
    assert _fresh(user).currency == "ILS"
    assert ExchangeRate.select().count() == 2