"""
tests/test_csv_reading.py
Reading CSV files: the encoding is detected first, the delimiter second,
and the preview and the import read the file the same way.
Run with: python -m pytest tests/test_csv_reading.py -v
"""

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, User, Transaction
from services.csv_import_service import read_csv_preview, import_transactions, SIGN_SIGNED

test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def setup_db():
    test_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(ALL_MODELS)
    yield
    test_db.drop_tables(ALL_MODELS)
    test_db.close()


def _file(tmp_path, name, text, encoding):
    path = tmp_path / name
    path.write_bytes(text.encode(encoding))
    return str(path)


def test_utf8_with_bom_has_clean_header(tmp_path):
    """Excel's "CSV UTF-8" adds an invisible BOM mark; it must not stick to the first header."""
    p = _file(tmp_path, "excel.csv", "Date,Amount\n01.03.2026,5\n", "utf-8-sig")
    assert read_csv_preview(p)["headers"][0] == "Date"


def test_utf8_non_latin_text(tmp_path):
    text = "Дата;Сумма;Описание\n01.03.2026;-45,50;Пятёрочка\n02.03.2026;-1,00;שופרסל\n"
    p = _file(tmp_path, "utf8.csv", text, "utf-8")
    rows = read_csv_preview(p)["rows"]
    assert [r[2] for r in rows] == ["Пятёрочка", "שופרסל"]


def test_russian_windows_1251(tmp_path):
    p = _file(tmp_path, "sber.csv", "Дата;Сумма\n01.03.2026;-45,50\n", "cp1251")
    preview = read_csv_preview(p)
    assert preview["encoding"] == "cp1251"
    assert preview["headers"] == ["Дата", "Сумма"]


def test_single_column_file_does_not_crash(tmp_path):
    """Before: a delimiter that couldn't be detected made the code try the NEXT encoding."""
    p = _file(tmp_path, "one.csv", "Amount\n5\n7\n", "utf-8")
    preview = read_csv_preview(p)
    assert preview["encoding"] == "utf-8-sig"
    assert preview["total_rows"] == 2


def test_empty_file_gives_clear_error(tmp_path):
    p = _file(tmp_path, "empty.csv", "", "utf-8")
    with pytest.raises(ValueError):
        read_csv_preview(p)


def test_import_reads_same_text_as_preview(tmp_path):
    user = User.create(name="Nick", currency="ILS")
    p = _file(tmp_path, "excel.csv", "Date,Amount,Note\n01.03.2026,-5,Кофе\n", "utf-8-sig")
    result = import_transactions(user, p, 0, 1, 2, "%d.%m.%Y", sign_mode=SIGN_SIGNED)
    assert result["imported"] == 1
    assert Transaction.get().note == "Кофе"