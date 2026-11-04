"""
tests/test_notifications.py
Budget notifications: delivered on every OS, counted honestly,
retried after a failure, reset at a new month.
Nothing is really shown: the system calls are replaced with fakes.
"""

import subprocess
import sys
import types
from datetime import date

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, User, Category
from services.budget_service import set_budget
from services.transaction_service import add_transaction
from utils import notifications
from utils.platform_utils import show_notification
from utils.i18n import TRANSLATIONS

test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def setup_db():
    test_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(ALL_MODELS)
    notifications._notified.clear()
    notifications._notified_month = None
    yield
    test_db.drop_tables(ALL_MODELS)
    test_db.close()


@pytest.fixture
def user():
    return User.create(name="Test User", currency="ILS")


@pytest.fixture
def over_budget(user):
    """This month: Groceries at 120% (danger), Cafe at 90% (warning)."""
    today = date.today()
    groceries = Category.create(user=None, name="Groceries", icon="🛒", type="expense")
    cafe = Category.create(user=None, name="Cafe", icon="☕", type="expense")
    set_budget(user, groceries, limit_cents=10000, year=today.year, month=today.month)
    set_budget(user, cafe, limit_cents=10000, year=today.year, month=today.month)
    add_transaction(user=user, type="expense", amount_cents=12000, category=groceries, tx_date=today)
    add_transaction(user=user, type="expense", amount_cents=9000, category=cafe, tx_date=today)
    return groceries, cafe


def _fake_delivery(monkeypatch, works: bool):
    shown = []

    def _show(title, message):
        shown.append(title)
        return works
    monkeypatch.setattr(notifications, "show_notification", _show)
    return shown


# ── Counting ──────────────────────────────────────────────────────────────────

def test_check_now_counts_only_delivered(monkeypatch, user, over_budget):
    _fake_delivery(monkeypatch, works=False)
    assert notifications.check_now(user) == (2, 0)

    _fake_delivery(monkeypatch, works=True)
    assert notifications.check_now(user) == (2, 2)


def test_check_now_nothing_to_report(monkeypatch, user):
    shown = _fake_delivery(monkeypatch, works=True)
    assert notifications.check_now(user) == (0, 0)
    assert shown == []


# ── Background check ──────────────────────────────────────────────────────────

def test_failed_notification_is_retried(monkeypatch, user, over_budget):
    _fake_delivery(monkeypatch, works=False)
    notifications._check_and_notify(user)
    assert notifications._notified == {}

    shown = _fake_delivery(monkeypatch, works=True)
    notifications._check_and_notify(user)
    assert len(shown) == 2

    shown = _fake_delivery(monkeypatch, works=True)
    notifications._check_and_notify(user)
    assert shown == []


def test_new_month_starts_fresh(monkeypatch, user, over_budget):
    groceries, _ = over_budget
    _fake_delivery(monkeypatch, works=True)
    today = date.today()
    notifications._check_and_notify(user, today=today)
    assert groceries.id in notifications._notified

    next_month = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
    notifications._check_and_notify(user, today=next_month)
    assert notifications._notified == {}


# ── Delivery per OS ───────────────────────────────────────────────────────────

def test_mac_uses_osascript_with_separate_arguments(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: calls.append(args))
    monkeypatch.setattr(sys, "platform", "darwin")
    assert show_notification('🚨 Budget exceeded: "Cafe"', "You spent 120") is True
    args = calls[0]
    assert args[0] == "osascript"
    assert args[-2:] == ['🚨 Budget exceeded: "Cafe"', "You spent 120"]


def test_mac_failure_returns_false(monkeypatch):
    def _fail(args, **kw):
        raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(subprocess, "run", _fail)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert show_notification("t", "m") is False


def test_windows_and_linux_use_plyer(monkeypatch):
    sent = []
    fake_plyer = types.SimpleNamespace(
        notification=types.SimpleNamespace(notify=lambda **kw: sent.append(kw["title"])))
    monkeypatch.setitem(sys.modules, "plyer", fake_plyer)
    for name in ("win32", "linux"):
        monkeypatch.setattr(sys, "platform", name)
        assert show_notification(name, "m") is True
    assert sent == ["win32", "linux"]


def test_plyer_without_backend_returns_false(monkeypatch):
    def _no_backend(**kw):
        raise NotImplementedError()
    fake_plyer = types.SimpleNamespace(notification=types.SimpleNamespace(notify=_no_backend))
    monkeypatch.setitem(sys.modules, "plyer", fake_plyer)
    monkeypatch.setattr(sys, "platform", "linux")
    assert show_notification("t", "m") is False


def test_new_texts_exist_in_every_language():
    for lang, strings in TRANSLATIONS.items():
        assert strings["notifications_failed"], lang
        assert strings["notifications_hint_mac"], lang