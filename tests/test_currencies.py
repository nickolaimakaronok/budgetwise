"""
tests/test_currencies.py
The one currency list (utils/currencies.py) and the Belarusian ruble
across formatting, typing an amount and CSV import.
"""

import pytest

from services.csv_import_service import parse_amount
from utils.currencies import CURRENCIES, CURRENCY_CODES, currency_label, currency_symbol
from utils.formatters import CURRENCY_SYMBOLS, format_money, parse_money, set_currency


@pytest.fixture
def byn():
    set_currency("BYN")
    yield
    set_currency("USD")                       # the default other tests expect


def test_every_currency_has_a_symbol_and_a_name():
    for code, (symbol, name) in CURRENCIES.items():
        assert len(code) == 3 and code.isupper()
        assert symbol and name


def test_formatter_uses_the_same_list():
    assert set(CURRENCY_SYMBOLS) == set(CURRENCY_CODES)
    assert CURRENCY_SYMBOLS["BYN"] == "Br"


def test_byn_formatting(byn):
    assert format_money(125050) == "1 250.50 Br"


def test_byn_typed_amount():
    assert parse_money("12,50 Br") == 1250
    assert parse_money("12.50") == 1250


def test_byn_in_bank_csv():
    assert parse_amount("-12,50 Br") == (1250, "expense")
    assert parse_amount("BYN 100") == (10000, "income")
    assert parse_amount("₪ 45.50") == (4550, "income")       # the old symbols still work


def test_labels_and_unknown_codes():
    assert currency_label("BYN") == "Br — Belarusian Ruble"
    assert currency_symbol("ILS") == "₪"
    assert currency_symbol("PLN") == "PLN"                   # not in the list → shown as the code