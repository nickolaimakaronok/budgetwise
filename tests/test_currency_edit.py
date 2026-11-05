"""
tests/test_currency_edit.py
The Add / Edit windows with a currency: the live "≈ 79.00 ₪" preview,
editing a purchase in another currency, and amounts shown in their own currency.
"""

from decimal import Decimal

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, Transaction, User
from services.currency_service import (
    add_transaction_in_currency, get_rate, preview_conversion, set_rate,
    update_transaction_in_currency,
)
from utils.formatters import format_money, parse_money, set_currency

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
    u = User.create(name="Nick", currency="ILS")
    set_rate(u, "EUR", "3.95")
    set_rate(u, "USD", "3.70")
    return u


def _fresh(tx):
    return Transaction.get_by_id(tx.id)


# ── Typing ────────────────────────────────────────────────────────────────────

def test_preview_while_typing():
    assert preview_conversion("20", "3.95") == 7900
    assert preview_conversion("20,50", "3,95") == 8098          # 80.975 → 80.98
    for amount, rate in [("", "3.95"), ("20", ""), ("2x", "3.95"), ("20", "abc"), ("inf", "3.95")]:
        assert preview_conversion(amount, rate) is None


def test_inf_is_not_an_amount():
    """Typing "inf" used to crash the Add window with OverflowError."""
    with pytest.raises(ValueError):
        parse_money("inf")


def test_amount_in_its_own_currency():
    set_currency("ILS")
    try:
        assert format_money(2000, currency="EUR") == "20.00 €"
        assert format_money(5000, currency="PLN") == "50.00 PLN"   # no symbol → the code
        assert format_money(7900) == "79.00 ₪"                      # main currency as before
    finally:
        set_currency("USD")


# ── Editing ───────────────────────────────────────────────────────────────────

def test_edit_keeps_the_purchase_rate(user):
    """The Edit window passes the purchase's own rate — a newer saved rate doesn't change it."""
    tx = add_transaction_in_currency(user, "expense", 2000, "EUR")
    set_rate(user, "EUR", "4.10")
    update_transaction_in_currency(tx, user, 3000, "EUR", tx.exchange_rate, note="dinner")
    tx = _fresh(tx)
    assert (tx.amount_cents, tx.original_amount_cents, tx.exchange_rate) == (11850, 3000, "3.95")
    assert tx.note == "dinner"


def test_edit_plain_purchase_into_euro(user):
    tx = add_transaction_in_currency(user, "expense", 7900)
    update_transaction_in_currency(tx, user, 2000, "EUR", "3.95")
    tx = _fresh(tx)
    assert (tx.currency, tx.original_amount_cents, tx.amount_cents) == ("EUR", 2000, 7900)


def test_edit_euro_purchase_back_to_main_currency(user):
    tx = add_transaction_in_currency(user, "expense", 2000, "EUR")
    update_transaction_in_currency(tx, user, 8000, None)
    tx = _fresh(tx)
    assert tx.amount_cents == 8000
    assert (tx.currency, tx.original_amount_cents, tx.exchange_rate) == (None, None, None)


def test_edit_to_another_currency_uses_its_saved_rate(user):
    tx = add_transaction_in_currency(user, "expense", 2000, "EUR")
    update_transaction_in_currency(tx, user, 1000, "USD")
    tx = _fresh(tx)
    assert (tx.currency, tx.amount_cents, tx.exchange_rate) == ("USD", 3700, "3.7")


def test_edit_zero_amount_is_rejected_and_nothing_changes(user):
    tx = add_transaction_in_currency(user, "expense", 2000, "EUR")
    with pytest.raises(ValueError):
        update_transaction_in_currency(tx, user, 0, "EUR", "3.95")
    tx = _fresh(tx)
    assert (tx.amount_cents, tx.original_amount_cents) == (7900, 2000)
    assert get_rate(user, "EUR") == Decimal("3.95")


def test_edit_works_on_the_app_database_object():
    """
    Regression: the models bound to the SAME database object the services use
    with `with db:` — as in the app. Nesting `with db:` inside a transaction
    crashed with "Attempting to close database while transaction is open".
    """
    import os
    from db.database import DB_PATH, db as app_db
    # Only ever on the throw-away folder from conftest.py — never on real data
    test_dir = os.environ.get("BUDGETWISE_DATA_DIR")
    assert test_dir and DB_PATH.startswith(os.path.abspath(test_dir))

    app_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    app_db.create_tables(ALL_MODELS)
    try:
        u = User.create(name="Nick", currency="ILS")
        set_rate(u, "EUR", "3.95")
        tx = add_transaction_in_currency(u, "expense", 2000, "EUR")
        update_transaction_in_currency(tx, u, 3000, "EUR", "3.95", note="dinner")
        tx = Transaction.get_by_id(tx.id)
        assert (tx.amount_cents, tx.original_amount_cents, tx.note) == (11850, 3000, "dinner")
    finally:
        app_db.drop_tables(ALL_MODELS)
        app_db.close()