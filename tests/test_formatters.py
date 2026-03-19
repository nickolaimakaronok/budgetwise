"""
tests/test_formatters.py
Unit tests for formatting utilities.
Run with: pytest tests/ -v
"""

import pytest
from utils.formatters import format_money, parse_money, percent, format_date_short, set_currency
from datetime import date


# Use USD for all tests
set_currency("USD")


class TestFormatMoney:
    def test_basic(self):
        assert "1 500" in format_money(150000)

    def test_with_cents(self):
        assert "1 500.50" in format_money(150050)

    def test_zero(self):
        assert "0.00" in format_money(0)

    def test_negative(self):
        result = format_money(-50000)
        assert "-" in result
        assert "500" in result

    def test_usd_symbol(self):
        assert "$" in format_money(100)

    def test_show_sign_positive(self):
        assert "+" in format_money(100, show_sign=True)

    def test_show_sign_negative(self):
        assert "+" not in format_money(-100, show_sign=True)


class TestParseMoney:
    def test_integer(self):
        assert parse_money("1500") == 150000

    def test_decimal_dot(self):
        assert parse_money("1500.50") == 150050

    def test_decimal_comma(self):
        assert parse_money("1500,50") == 150050

    def test_with_spaces(self):
        assert parse_money("1 500") == 150000

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_money("abc")

    def test_roundtrip(self):
        """Converting to string and back should not lose data."""
        original = 99999
        parsed = parse_money(str(original / 100))
        assert parsed == original


class TestPercent:
    def test_half(self):
        assert percent(50, 100) == 50.0

    def test_zero_total(self):
        assert percent(100, 0) == 0.0

    def test_over_100(self):
        assert percent(150, 100) == 150.0


class TestFormatDateShort:
    def test_march(self):
        assert format_date_short(date(2025, 3, 19)) == "19 Mar"

    def test_january(self):
        assert format_date_short(date(2025, 1, 1)) == "1 Jan"
