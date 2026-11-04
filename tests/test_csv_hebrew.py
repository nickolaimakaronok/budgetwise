"""
tests/test_csv_hebrew.py
Old Windows encodings: Hebrew (Windows-1255) used to be read as Cyrillic
(Windows-1251) — "שופרסל" turned into "щефшсм". Also Excel's UTF-16 "Unicode text".
Run with: python -m pytest tests/test_csv_hebrew.py -v
"""

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, User, Transaction
from services.csv_import_service import (
    detect_encoding, read_csv_preview, import_transactions, SIGN_SIGNED,
)

HEBREW_CSV  = "תאריך;סכום;תיאור\n01.03.2026;-45.50;שופרסל\n02.03.2026;-12.00;קפה ₪\n"
RUSSIAN_CSV = "Дата;Сумма;Описание\n01.03.2026;-45,50;Пятёрочка\n02.03.2026;-12,00;кофе\n"

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


def test_hebrew_windows_1255(tmp_path):
    p = _file(tmp_path, "leumi.csv", HEBREW_CSV, "cp1255")
    preview = read_csv_preview(p)
    assert preview["encoding"] == "cp1255"
    assert preview["headers"] == ["תאריך", "סכום", "תיאור"]
    assert preview["rows"][0][2] == "שופרסל"


def test_russian_is_not_mistaken_for_hebrew(tmp_path):
    p = _file(tmp_path, "sber.csv", RUSSIAN_CSV, "cp1251")
    preview = read_csv_preview(p)
    assert preview["encoding"] == "cp1251"
    assert preview["rows"][0][2] == "Пятёрочка"


def test_utf16_excel_unicode_text(tmp_path):
    text = "Date\tAmount\tNote\n01.03.2026\t-5\tשופרסל\n"
    p = _file(tmp_path, "excel.txt", text, "utf-16")
    preview = read_csv_preview(p)
    assert preview["encoding"] == "utf-16"
    assert preview["delimiter"] == "\t"
    assert preview["rows"][0] == ["01.03.2026", "-5", "שופרסל"]


def test_plain_ascii_is_utf8():
    assert detect_encoding(b"Date,Amount\n01.03.2026,5\n") == "utf-8-sig"


def test_import_hebrew_file_end_to_end(tmp_path):
    user = User.create(name="Nick", currency="ILS")
    p = _file(tmp_path, "leumi.csv", HEBREW_CSV, "cp1255")
    result = import_transactions(user, p, 0, 1, 2, "%d.%m.%Y", sign_mode=SIGN_SIGNED)
    assert result["imported"] == 2
    notes = sorted(tx.note for tx in Transaction.select())
    assert notes == sorted(["שופרסל", "קפה ₪"])