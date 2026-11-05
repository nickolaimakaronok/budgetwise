"""
tests/test_currency_recurring_csv.py
Purchases in another currency in the places that make transactions for you:
monthly copies of a recurring series, CSV export and CSV import.
"""

import csv
from datetime import date

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, Transaction, User
from services.csv_export_service import export_transactions_csv
from services.csv_import_service import SIGN_ALL_EXPENSE, SIGN_SIGNED, import_transactions
from services.currency_service import add_transaction_in_currency, delete_rate, set_rate
from services.transaction_service import create_recurring_for_month, filter_transactions, get_totals
from utils.i18n import set_language

test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def setup_db():
    set_language("en")
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
    return u


def _copies(tpl):
    return list(Transaction.select()
                .where(Transaction.recurring_parent == tpl.id)
                .order_by(Transaction.date))


def _csv(tmp_path, text):
    path = tmp_path / "statement.csv"
    path.write_text(text, encoding="utf-8")
    return str(path)


# ── Recurring ─────────────────────────────────────────────────────────────────

def test_euro_subscription_copy_uses_todays_rate(user):
    """10 € a month: September at 3.95, then the rate becomes 4.00 → October costs 40 ₪."""
    tpl = add_transaction_in_currency(user, "expense", 1000, "EUR",
                                      tx_date=date(2026, 9, 5), note="Netflix", is_recurring=True)
    set_rate(user, "EUR", "4.00")
    create_recurring_for_month(user, 2026, 10)

    [copy] = _copies(tpl)
    assert (copy.amount_cents, copy.currency, copy.original_amount_cents, copy.exchange_rate) \
        == (4000, "EUR", 1000, "4")
    assert copy.date == date(2026, 10, 5)
    assert Transaction.get_by_id(tpl.id).amount_cents == 3950        # the template keeps its own


def test_copy_falls_back_to_template_rate_when_rate_deleted(user):
    tpl = add_transaction_in_currency(user, "expense", 1000, "EUR",
                                      tx_date=date(2026, 9, 5), is_recurring=True)
    delete_rate(user, "EUR")
    create_recurring_for_month(user, 2026, 10)
    [copy] = _copies(tpl)
    assert (copy.amount_cents, copy.exchange_rate) == (3950, "3.95")


def test_plain_series_is_unchanged(user):
    tpl = add_transaction_in_currency(user, "expense", 500000,
                                      tx_date=date(2026, 9, 1), note="rent", is_recurring=True)
    create_recurring_for_month(user, 2026, 11)
    copies = _copies(tpl)
    assert [c.amount_cents for c in copies] == [500000, 500000]
    assert all(c.currency is None for c in copies)


# ── Export ────────────────────────────────────────────────────────────────────

def test_export_shows_what_was_actually_paid(user, tmp_path):
    add_transaction_in_currency(user, "expense", 2000, "EUR", tx_date=date(2026, 11, 2), note="dinner")
    add_transaction_in_currency(user, "expense", 5000, tx_date=date(2026, 11, 1), note="taxi")
    path = str(tmp_path / "out.csv")
    export_transactions_csv(filter_transactions(user), path)

    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0][6:] == ["Original amount", "Currency", "Rate"]
    assert rows[1][3:] == ["-79.00", "dinner", "", "-20.00", "EUR", "3.95"]
    assert rows[2][3:] == ["-50.00", "taxi", "", "", "", ""]


def test_export_with_foreign_rows_imports_back_with_same_totals(user, tmp_path):
    add_transaction_in_currency(user, "expense", 2000, "EUR", note="dinner")
    add_transaction_in_currency(user, "income", 100000, note="salary")
    path = str(tmp_path / "out.csv")
    export_transactions_csv(filter_transactions(user), path)

    other = User.create(name="Other", currency="ILS")
    import_transactions(other, path, 0, 3, 4, "%d.%m.%Y", sign_mode=SIGN_SIGNED)
    assert get_totals(other) == get_totals(user)


# ── Import ────────────────────────────────────────────────────────────────────

def test_import_euro_statement(user, tmp_path):
    path = _csv(tmp_path, "Date,Amount,Description\n02.11.2026,20.00,Dinner\n03.11.2026,\"10,50 EUR\",Museum\n")
    result = import_transactions(user, path, 0, 1, 2, "%d.%m.%Y",
                                 sign_mode=SIGN_ALL_EXPENSE, currency="EUR", rate="4")
    assert result["imported"] == 2
    rows = [(tx.amount_cents, tx.currency, tx.original_amount_cents, tx.exchange_rate)
            for tx in Transaction.select().order_by(Transaction.date)]
    assert rows == [(8000, "EUR", 2000, "4"), (4200, "EUR", 1050, "4")]


def test_import_uses_saved_rate_when_none_given(user, tmp_path):
    path = _csv(tmp_path, "Date,Amount\n02.11.2026,-20.00\n")
    import_transactions(user, path, 0, 1, None, "%d.%m.%Y", currency="EUR")
    tx = Transaction.get()
    assert (tx.amount_cents, tx.exchange_rate) == (7900, "3.95")


def test_import_without_any_rate_stops_before_the_first_row(user, tmp_path):
    path = _csv(tmp_path, "Date,Amount\n02.11.2026,-20.00\n03.11.2026,-5.00\n")
    with pytest.raises(ValueError):
        import_transactions(user, path, 0, 1, None, "%d.%m.%Y", currency="USD")
    assert Transaction.select().count() == 0


def test_import_in_main_currency_is_plain(user, tmp_path):
    path = _csv(tmp_path, "Date,Amount\n02.11.2026,-20.00\n")
    import_transactions(user, path, 0, 1, None, "%d.%m.%Y", currency="ILS")
    tx = Transaction.get()
    assert (tx.amount_cents, tx.currency) == (2000, None)