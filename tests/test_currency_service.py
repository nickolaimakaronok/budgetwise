"""
tests/test_currency_service.py
Purchases in other currencies: exact Decimal conversion, saved rates,
and the rate fixed at the moment of purchase.
"""

from datetime import date
from decimal import Decimal

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, Category, ExchangeRate, Transaction, User
from services.budget_service import get_budget_status, set_budget
from services.currency_service import (
    add_transaction_in_currency, convert_cents, delete_rate, format_rate,
    get_rate, get_rates, normalize_currency_code, parse_rate, set_rate,
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
    return User.create(name="Nick", currency="ILS")


# ── Arithmetic ────────────────────────────────────────────────────────────────

def test_convert_is_exact_where_float_is_not():
    # 0.50 EUR × 1.15 = 0.575 → 0.58; float gives 57.4999… cents → 0.57
    assert 50 * float("1.15") < 57.5
    assert convert_cents(50, Decimal("1.15")) == 58


def test_convert_rounds_half_up():
    assert convert_cents(1, Decimal("2.5")) == 3          # round(2.5) would be 2
    assert convert_cents(2000, Decimal("3.95")) == 7900
    assert convert_cents(123456789, Decimal("1.1")) == 135802468


def test_parse_rate_accepts_comma_and_rejects_nonsense():
    assert parse_rate("3,95") == Decimal("3.95")
    assert parse_rate(" 4 ") == Decimal("4")
    for bad in ["", "abc", "0", "-1", "inf", "nan"]:
        with pytest.raises(ValueError):
            parse_rate(bad)


def test_format_rate_drops_trailing_zeros():
    assert format_rate(Decimal("4.00")) == "4"
    assert format_rate(Decimal("3.950")) == "3.95"
    assert format_rate(Decimal("0.0105")) == "0.0105"


def test_currency_codes():
    assert normalize_currency_code(" eur ") == "EUR"
    assert normalize_currency_code("PLN") == "PLN"            # not in the list — still fine
    for bad in ["", "EURO", "€", "E1R"]:
        with pytest.raises(ValueError):
            normalize_currency_code(bad)


# ── Saved rates ───────────────────────────────────────────────────────────────

def test_set_rate_replaces_old_rate(user):
    set_rate(user, "EUR", "3.95")
    set_rate(user, "eur", "4,10")
    assert get_rate(user, "EUR") == Decimal("4.10")
    assert ExchangeRate.select().count() == 1


def test_main_currency_needs_no_rate(user):
    with pytest.raises(ValueError):
        set_rate(user, "ILS", "1")


def test_rates_list_delete_and_users_are_separate(user):
    other = User.create(name="Other", currency="USD")
    set_rate(user, "USD", "3.70")
    set_rate(user, "EUR", "3.95")
    set_rate(other, "EUR", "0.92")
    assert [r.currency for r in get_rates(user)] == ["EUR", "USD"]
    assert get_rate(other, "EUR") == Decimal("0.92")
    assert delete_rate(user, "USD") is True
    assert get_rate(user, "USD") is None
    assert delete_rate(user, "USD") is False


# ── Purchases ─────────────────────────────────────────────────────────────────

def test_purchase_in_euro_is_converted_with_saved_rate(user):
    set_rate(user, "EUR", "3.95")
    tx = add_transaction_in_currency(user, "expense", 2000, "EUR", note="coffee")
    assert tx.amount_cents == 7900
    assert (tx.currency, tx.original_amount_cents, tx.exchange_rate) == ("EUR", 2000, "3.95")
    assert tx.is_foreign


def test_rate_of_one_purchase_overrides_saved_rate(user):
    set_rate(user, "EUR", "3.95")
    tx = add_transaction_in_currency(user, "expense", 2000, "EUR", rate="4.00")
    assert tx.amount_cents == 8000
    assert tx.exchange_rate == "4"
    assert get_rate(user, "EUR") == Decimal("3.95")           # the saved rate is untouched


def test_no_rate_no_purchase(user):
    with pytest.raises(ValueError):
        add_transaction_in_currency(user, "expense", 2000, "EUR")


def test_main_currency_purchase_is_plain(user):
    tx = add_transaction_in_currency(user, "expense", 5000, "ILS")
    assert tx.amount_cents == 5000
    assert tx.currency is None and not tx.is_foreign


def test_new_rate_does_not_change_past_purchases(user):
    set_rate(user, "EUR", "3.95")
    old = add_transaction_in_currency(user, "expense", 2000, "EUR")
    set_rate(user, "EUR", "4.10")
    new = add_transaction_in_currency(user, "expense", 2000, "EUR")
    assert Transaction.get_by_id(old.id).amount_cents == 7900
    assert new.amount_cents == 8200


def test_totals_and_budgets_see_the_converted_amount(user):
    cafe = Category.create(user=None, name="Cafe", icon="☕", type="expense")
    tx_date = date(2026, 11, 5)
    set_budget(user, cafe, limit_cents=10000, year=2026, month=11)
    set_rate(user, "EUR", "3.95")
    add_transaction_in_currency(user, "expense", 2000, "EUR", category=cafe, tx_date=tx_date)
    add_transaction_in_currency(user, "expense", 1000, category=cafe, tx_date=tx_date)
    assert get_totals(user)["expense_cents"] == 8900
    status = get_budget_status(user, 2026, 11)[0]
    assert status["spent_cents"] == 8900