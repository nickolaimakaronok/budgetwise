"""
tests/test_csv_import.py
CSV import: the user chooses how the amount sign is read, and categories
are only matched within the same type.
(Before: every amount without a minus was imported as INCOME.)
Run with: python -m pytest tests/test_csv_import.py -v
"""

import csv

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, User, Category, Transaction
from services.csv_import_service import (
    import_transactions, guess_sign_mode, parse_amount,
    SIGN_SIGNED, SIGN_ALL_EXPENSE, SIGN_ALL_INCOME,
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


def _write_csv(path, rows, header=("Date", "Amount", "Description")):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return str(path)


def _imported():
    return {tx.note: (tx.type, tx.amount_cents) for tx in Transaction.select()}


def test_unsigned_card_statement_as_expenses(user, tmp_path):
    p = _write_csv(tmp_path / "card.csv", [["01.03.2026", "45.50", "Supermarket"],
                                            ["02.03.2026", "12.00", "Coffee"]])
    r = import_transactions(user, p, 0, 1, 2, "%d.%m.%Y", sign_mode=SIGN_ALL_EXPENSE)
    assert r["imported"] == 2
    assert _imported() == {"Supermarket": ("expense", 4550), "Coffee": ("expense", 1200)}


def test_signed_file(user, tmp_path):
    p = _write_csv(tmp_path / "bank.csv", [["01.03.2026", "-45.50", "Shop"],
                                            ["02.03.2026", "3000", "Salary"],
                                            ["03.03.2026", "\u221210", "Typographic minus"]])
    import_transactions(user, p, 0, 1, 2, "%d.%m.%Y", sign_mode=SIGN_SIGNED)
    assert _imported() == {"Shop": ("expense", 4550), "Salary": ("income", 300000),
                           "Typographic minus": ("expense", 1000)}


def test_all_income_mode(user, tmp_path):
    p = _write_csv(tmp_path / "in.csv", [["01.03.2026", "-5", "refund"]])
    import_transactions(user, p, 0, 1, 2, "%d.%m.%Y", sign_mode=SIGN_ALL_INCOME)
    assert _imported() == {"refund": ("income", 500)}


def test_unknown_sign_mode_rejected(user, tmp_path):
    p = _write_csv(tmp_path / "x.csv", [["01.03.2026", "1", "x"]])
    with pytest.raises(ValueError):
        import_transactions(user, p, 0, 1, 2, "%d.%m.%Y", sign_mode="banana")


def test_guess_sign_mode():
    assert guess_sign_mode([["d", "45.50"], ["d", "-3"]], 1) == SIGN_SIGNED
    assert guess_sign_mode([["d", "45.50"], ["d", "(3.00)"]], 1) == SIGN_SIGNED
    assert guess_sign_mode([["d", "45.50"], ["d", "3"]], 1) == SIGN_ALL_EXPENSE
    assert guess_sign_mode([["only-one-column"]], 1) == SIGN_ALL_EXPENSE   # short rows don't crash


def test_category_must_match_type(user, tmp_path):
    Category.create(user=None, name="Salary", type="income")
    p = _write_csv(tmp_path / "x.csv", [["01.03.2026", "10", "Salary advance fee"]])
    import_transactions(user, p, 0, 1, 2, "%d.%m.%Y", sign_mode=SIGN_ALL_EXPENSE)
    assert Transaction.get().category is None          # an expense never lands in "Salary"


def test_category_matched_within_type(user, tmp_path):
    groceries = Category.create(user=None, name="Groceries", type="expense")
    p = _write_csv(tmp_path / "x.csv", [["01.03.2026", "10", "groceries"]])
    import_transactions(user, p, 0, 1, 2, "%d.%m.%Y", sign_mode=SIGN_ALL_EXPENSE)
    assert Transaction.get().category_id == groceries.id


def test_parse_amount_formats():
    assert parse_amount("-1.234,50") == (123450, "expense")      # European
    assert parse_amount("1,234.50") == (123450, "income")        # American
    assert parse_amount("(45.50)") == (4550, "expense")          # accounting style
    assert parse_amount("\u221245.50 ₪") == (4550, "expense")     # typographic minus + symbol