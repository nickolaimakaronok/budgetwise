"""
tests/test_csv_export.py
CSV export: Type column, signed amounts, UTF-8 with BOM, the same rows as
on screen (filters + search + tags) — and the file imports back unchanged.
Run with: python -m pytest tests/test_csv_export.py -v
"""

import csv
from datetime import date

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, User, Category
from services.transaction_service import add_transaction, filter_transactions, get_totals
from services.tag_service import set_transaction_tags
from services.csv_export_service import export_transactions_csv, signed_amount_text
from services.csv_import_service import import_transactions, SIGN_SIGNED
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
    return User.create(name="Test User", currency="ILS")


@pytest.fixture
def groceries():
    return Category.create(user=None, name="Продукты", icon="🛒", type="expense")


@pytest.fixture
def salary():
    return Category.create(user=None, name="Salary", type="income")


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def test_signed_amounts_type_column_and_bom(user, groceries, salary, tmp_path):
    expense = add_transaction(user, "expense", 45050, groceries, date(2026, 3, 1), "Магазин")
    add_transaction(user, "income", 5, salary, date(2026, 3, 2), "tiny")
    set_transaction_tags(expense, user, ["food"])
    path = str(tmp_path / "out.csv")

    assert export_transactions_csv(filter_transactions(user), path) == 2

    assert open(path, "rb").read().startswith(b"\xef\xbb\xbf")      # BOM for Excel
    rows = _read(path)
    assert rows[0] == ["Date", "Type", "Category", "Amount", "Note", "Tags",
                       "Original amount", "Currency", "Rate"]
    assert rows[1] == ["02.03.2026", "Income", "Salary", "0.05", "tiny", "", "", "", ""]
    assert rows[2] == ["01.03.2026", "Expense", "Продукты", "-450.50", "Магазин", "#food", "", "", ""]


def test_export_respects_search_and_tag(user, groceries, tmp_path):
    a = add_transaction(user, "expense", 100, groceries, note="coffee")
    add_transaction(user, "expense", 200, groceries, note="bread")
    set_transaction_tags(a, user, ["work"])
    path = str(tmp_path / "out.csv")

    export_transactions_csv(filter_transactions(user, search="#work"), path)

    rows = _read(path)
    assert len(rows) == 2                     # header + the one matching row
    assert rows[1][4] == "coffee"


def test_headers_follow_ui_language(user, groceries, tmp_path):
    add_transaction(user, "expense", 100, groceries, note="x")
    set_language("ru")
    path = str(tmp_path / "out.csv")
    export_transactions_csv(filter_transactions(user), path)
    rows = _read(path)
    assert rows[0][:2] == ["Дата", "Тип"]
    assert rows[1][1] == "Расход"


def test_signed_amount_text_no_float_errors():
    class Tx:
        def __init__(self, cents, kind):
            self.amount_cents, self.type = cents, kind
    assert signed_amount_text(Tx(1, "expense")) == "-0.01"
    assert signed_amount_text(Tx(123456789, "income")) == "1234567.89"
    assert signed_amount_text(Tx(28, "expense")) == "-0.28"


def test_export_then_import_gives_same_totals(user, groceries, salary, tmp_path):
    add_transaction(user, "expense", 123456, groceries, date(2026, 3, 1), "rent")
    add_transaction(user, "income", 999, salary, date(2026, 3, 2), "bonus")
    before = get_totals(user)
    path = str(tmp_path / "out.csv")
    export_transactions_csv(filter_transactions(user), path)

    other = User.create(name="Other")
    import_transactions(other, path, 0, 3, 4, "%d.%m.%Y", sign_mode=SIGN_SIGNED)

    assert get_totals(other) == before