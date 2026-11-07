"""
tests/test_rates_online.py
Rates from the internet — tested without the internet: _http_get is replaced
by a fake. Checks how the answer is read and turned into "1 EUR = 3.95 ₪",
what happens offline, and that an update never touches past purchases.
"""

import http.client
import json
import urllib.error
from datetime import date
from decimal import Decimal

import pytest
from peewee import SqliteDatabase

import services.rates_online as rates_online
from models.models import ALL_MODELS, ExchangeRate, Transaction, User
from services.currency_service import add_transaction_in_currency, get_rate, set_rate
from services.rates_online import RatesUnavailable, fetch_rate, fetch_rates, update_saved_rates

test_db = SqliteDatabase(":memory:")

# What Frankfurter v2 answers for base=ILS: how much 1 ILS is in each currency
V2_ANSWER = [
    {"date": "2026-11-06", "base": "ILS", "quote": "EUR", "rate": 0.2531646},
    {"date": "2026-11-06", "base": "ILS", "quote": "USD", "rate": 0.27027},
    {"date": "2026-11-06", "base": "ILS", "quote": "BYN", "rate": 0.8},
    {"date": "2026-11-06", "base": "ILS", "quote": "RUB", "rate": 21.7},
    {"date": "2026-11-06", "base": "ILS", "quote": "USDT", "rate": 0.27},    # crypto, 4 letters
]


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


@pytest.fixture
def net(monkeypatch):
    """A fake internet: remembers the URLs asked for; answers with .answer, .raw or raises .error."""
    class FakeNet:
        def __init__(self):
            self.answer, self.raw, self.error, self.urls = V2_ANSWER, None, None, []

    fake = FakeNet()

    def fake_get(url):
        fake.urls.append(url)
        if fake.error is not None:
            raise fake.error
        return fake.raw if fake.raw is not None else json.dumps(fake.answer).encode()

    monkeypatch.setattr(rates_online, "_http_get", fake_get)
    return fake


# ── Reading the answer ────────────────────────────────────────────────────────

def test_rates_are_turned_into_main_currency(net):
    result = fetch_rates("ILS", ["EUR", "USD", "BYN", "RUB"])
    assert result.rates == {
        "EUR": Decimal("3.95"),          # 1 / 0.2531646 = 3.9499993… → 3.95000
        "USD": Decimal("3.7"),           # 1 / 0.27027   = 3.7000037… → 3.70000
        "BYN": Decimal("1.25"),
        "RUB": Decimal("0.0460829"),     # 1 / 21.7, six significant digits
    }
    assert result.on == date(2026, 11, 6)


def test_one_request_with_the_main_currency_as_base(net):
    fetch_rates("ILS", ["EUR", "USD"])
    fetch_rates("ILS", ["EUR"], on_date=date(2026, 9, 15))
    latest, old = net.urls
    assert "base=ILS" in latest and "date=" not in latest
    assert "date=2026-09-15" in old


def test_unknown_currencies_and_the_main_one_are_left_out(net):
    assert list(fetch_rates("ILS", ["EUR", "XYZ", "ILS"]).rates) == ["EUR"]


def test_old_v1_answer_is_read_too(net):
    net.answer = {"amount": 1.0, "base": "ILS", "date": "2026-11-06", "rates": {"EUR": 0.25}}
    result = fetch_rates("ILS", ["EUR"])
    assert result.rates == {"EUR": Decimal("4")}
    assert result.on == date(2026, 11, 6)


def test_bad_rates_are_skipped(net):
    net.answer = [{"quote": "EUR", "rate": 0}, {"quote": "USD", "rate": -1},
                  {"quote": "GBP", "rate": "abc"}, {"quote": "BYN", "rate": None},
                  {"quote": "RUB", "rate": 21.7}, "not a row"]
    assert list(fetch_rates("ILS", ["EUR", "USD", "GBP", "BYN", "RUB"]).rates) == ["RUB"]


def test_fetch_one_rate(net):
    assert fetch_rate("ILS", "eur") == Decimal("3.95")
    with pytest.raises(RatesUnavailable):
        fetch_rate("ILS", "XYZ")


# ── No internet, broken answers ───────────────────────────────────────────────

@pytest.mark.parametrize("error", [
    urllib.error.URLError("no internet"),
    TimeoutError("timed out"),
    OSError("network is down"),
    urllib.error.HTTPError("https://x", 422, "invalid currency", {}, None),
    http.client.IncompleteRead(b"[{"),
])
def test_no_internet_is_one_clear_error(net, error):
    net.error = error
    with pytest.raises(RatesUnavailable):
        fetch_rates("ILS", ["EUR"])


@pytest.mark.parametrize("raw", [b"<html>Bad gateway</html>", b'{"status": 422, "message": "invalid"}'])
def test_unreadable_answer_is_one_clear_error(net, raw):
    net.raw = raw
    with pytest.raises(RatesUnavailable):
        fetch_rates("ILS", ["EUR"])


# ── Updating the saved rates ──────────────────────────────────────────────────

def test_update_refreshes_only_the_saved_currencies(user, net):
    set_rate(user, "EUR", "3.80")
    set_rate(user, "BYN", "1.10")
    set_rate(user, "XYZ", "2")                       # a currency the service doesn't know
    result = update_saved_rates(user)

    assert result.updated == {"BYN": Decimal("1.25"), "EUR": Decimal("3.95")}
    assert result.missing == ["XYZ"]
    assert result.on == date(2026, 11, 6)
    assert get_rate(user, "EUR") == Decimal("3.95")
    assert get_rate(user, "XYZ") == Decimal("2")     # kept as it was
    assert ExchangeRate.select().count() == 3        # USD and RUB were not added


def test_update_never_touches_past_purchases(user, net):
    """The promise: a new rate is for new purchases — a past purchase keeps its own."""
    set_rate(user, "EUR", "3.80")
    tx = add_transaction_in_currency(user, "expense", 2000, "EUR", note="dinner")
    update_saved_rates(user)

    tx = Transaction.get_by_id(tx.id)
    assert (tx.amount_cents, tx.original_amount_cents, tx.exchange_rate) == (7600, 2000, "3.8")
    assert Transaction.select().count() == 1
    assert get_rate(user, "EUR") == Decimal("3.95")  # only the saved rate changed


def test_offline_update_changes_nothing(user, net):
    set_rate(user, "EUR", "3.80")
    net.error = urllib.error.URLError("no internet")
    with pytest.raises(RatesUnavailable):
        update_saved_rates(user)
    assert get_rate(user, "EUR") == Decimal("3.80")


def test_no_saved_rates_no_request(user, net):
    result = update_saved_rates(user)
    assert (result.updated, result.missing) == ({}, [])
    assert net.urls == []