"""
tests/test_smoke_big.py
One long walk through the app the way a user does it — real windows, real
buttons, the same database object as the app (in the throw-away folder from
conftest.py):

  onboarding → every page → exchange rates → add transactions (main currency,
  euro, recurring, tags, Cmd+N, wrong input) → search and filters → edit and
  delete → CSV export, CSV import (own export + a euro statement), PDF report →
  budget limits → goals → analytics → settings (profile, rates, categories,
  theme, languages, backup, notifications) → change the main currency and back.

The other tests check the services one by one. This one checks that the
windows call them correctly — Add calls "add", Edit saves the note — and that
no window crashes. Buttons are pressed through their own command (invoke),
so a wrong command= is caught too.

Needs a screen: skipped where Tk can't open a window (Linux without a display).
System dialogs (message boxes, file pickers), opening Finder/Explorer and
system notifications are replaced, so nothing waits for a click.
"""

import csv
import os
import tkinter
from datetime import date, timedelta
from tkinter import filedialog, messagebox

import pytest

import customtkinter as ctk
from models.models import ALL_MODELS, Budget, Category, ExchangeRate, Goal, Transaction, User
from utils.formatters import set_currency
from utils.i18n import months_list, set_language, t


# ── Setup ─────────────────────────────────────────────────────────────────────

def _can_open_window() -> bool:
    try:
        root = tkinter.Tk()
        root.destroy()
        return True
    except tkinter.TclError:
        return False


pytestmark = pytest.mark.skipif(not _can_open_window(), reason="no screen for Tk windows")


class Recorder:
    """What the replaced system dialogs were asked to show."""

    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.infos, self.errors, self.tk_errors = [], [], []
        self.opened_folders, self.notifications = [], []
        self.save_path = self.open_path = ""
        self.expected_errors = 0


@pytest.fixture
def rec(monkeypatch, tmp_path):
    from db.database import DB_PATH, db as app_db
    from db.migrations import run as run_migrations
    import ui.pages.settings as settings_page
    import utils.notifications as notifications

    # Only ever on the throw-away folder from conftest.py — never on real data
    test_dir = os.environ.get("BUDGETWISE_DATA_DIR")
    assert test_dir and DB_PATH.startswith(os.path.abspath(test_dir))

    app_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    app_db.drop_tables(ALL_MODELS)
    run_migrations()                                  # tables + system categories, as at startup

    r = Recorder(tmp_path)
    monkeypatch.setattr(messagebox, "showinfo", lambda title, msg, **k: r.infos.append(msg))
    monkeypatch.setattr(messagebox, "showwarning", lambda title, msg, **k: r.infos.append(msg))
    monkeypatch.setattr(messagebox, "showerror", lambda title, msg, **k: r.errors.append(msg))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: r.save_path)
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: r.open_path)
    monkeypatch.setattr(settings_page, "open_path", lambda path: r.opened_folders.append(path) or True)
    monkeypatch.setattr(notifications, "show_notification",
                        lambda title, msg: r.notifications.append(title) or True)
    yield r

    set_language("en")
    set_currency("USD")
    app_db.drop_tables(ALL_MODELS)
    app_db.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def pump(app, ms: int = 0):
    """Lets the windows draw and run their callbacks (ms: also wait that long)."""
    app.update()
    if ms:
        app.after(ms)
        app.update()


def find(root, cls) -> list:
    """All widgets of class cls inside root — dialogs too (they are children of pages)."""
    found, stack = [], [root]
    while stack:
        widget = stack.pop()
        if isinstance(widget, cls):
            found.append(widget)
        stack.extend(widget.winfo_children())
    return found


def window(app, cls):
    """The one open window of this class; waits a moment so it finishes opening."""
    pump(app, 250)
    [win] = find(app, cls)
    return win


def click(root, text: str):
    """Presses the button with this text inside root — through its own command."""
    buttons = [b for b in find(root, ctk.CTkButton) if b.cget("text") == text]
    assert len(buttons) == 1, f"expected one button {text!r}, found {len(buttons)}"
    buttons[0].invoke()


def row_of(root, label_text: str):
    """The frame that holds the label with this text (one row of a list)."""
    [label] = [w for w in find(root, ctk.CTkLabel) if w.cget("text") == label_text]
    return label.master


def type_in(entry, text: str):
    entry.delete(0, "end")
    entry.insert(0, text)


def expect_error(r: Recorder, message: str, action):
    """action must show exactly this error message — and save nothing."""
    before = Transaction.select().count()
    action()
    r.expected_errors += 1
    assert r.errors[-1] == message
    assert len(r.errors) == r.expected_errors
    assert Transaction.select().count() == before


def tx(note: str) -> Transaction:
    """The first transaction with this note (importing our own export makes a second one)."""
    found = Transaction.select().where(Transaction.note == note).order_by(Transaction.id).first()
    assert found is not None, f"no transaction {note!r}"
    return found


def category_key(cat_map: dict, kind: str) -> str:
    """The option-menu text of the first category of this type ("expense" / "income")."""
    return next(key for key, cat in cat_map.items() if cat.type == kind)


# ── The walk ──────────────────────────────────────────────────────────────────

def test_smoke_big(rec):
    from ui.app import App

    user = _onboarding()
    app = App(user)
    app.geometry("1200x800+0+0")

    def on_tk_error(exc_type, exc, tb):
        # a late callback of a window that was already closed is not our bug
        text = str(exc)
        if isinstance(exc, tkinter.TclError) and ("bad window path" in text or "invalid command" in text):
            return
        import traceback
        rec.tk_errors.append("".join(traceback.format_exception(exc_type, exc, tb)))
    app.report_callback_exception = on_tk_error

    try:
        pump(app, 300)
        _visit_every_page(app)
        _exchange_rates(app, rec, user)
        _add_transactions(app, rec, user)
        _search_and_filters(app, rec)
        _edit_and_delete(app, rec, user)
        _export_and_import(app, rec, user)
        _budget(app, rec)
        _goals(app, rec)
        _analytics(app)
        _settings(app, rec, user)
        _change_main_currency(app, rec)
        _visit_every_page(app)
        pump(app, 300)
    finally:
        app.destroy()

    assert rec.tk_errors == []
    assert len(rec.errors) == rec.expected_errors     # no error message nobody expected


def _onboarding() -> User:
    from ui.pages.onboarding import CURRENCY_LABELS, OnboardingWindow

    win = OnboardingWindow()
    win.update()
    win._select_language("ru")                          # step 1: the "Русский" button
    win._go_step_2()
    win._go_step_3()                                     # no name yet → stays on step 2
    assert win.step == 2 and win.error_label.cget("text") == t("name_required")
    win.name_entry.insert(0, "Nick")
    win.currency_var.set(CURRENCY_LABELS["ILS"])
    win._go_step_3()
    assert win.step == 3
    win._finish()                                        # the "Start" button — closes the window
    result = OnboardingWindow._result
    assert result == {"name": "Nick", "currency": "ILS", "language": "ru"}

    # what main.py does next
    user = User.create(**result)
    set_language(user.language)
    set_currency(user.currency)
    return user


def _visit_every_page(app):
    from utils.constants import NAV_ITEMS
    for page_id, _emoji, _key in NAV_ITEMS:
        app.nav_buttons[page_id].invoke()
        pump(app)
        assert app.current_frame is not None, page_id


def _exchange_rates(app, rec, user):
    app.nav_buttons["settings"].invoke()
    pump(app)
    page = app.current_frame
    add_row = page.new_rate_code.master

    page.new_rate_code.set("EURO")
    type_in(page.new_rate_value, "3.95")
    expect_error(rec, t("currency_code_invalid"), lambda: click(add_row, t("add")))
    page.new_rate_code.set("ILS")
    expect_error(rec, t("rate_is_main").format("ILS"), lambda: click(add_row, t("add")))
    page.new_rate_code.set("EUR")
    type_in(page.new_rate_value, "abc")
    expect_error(rec, t("rate_invalid"), lambda: click(add_row, t("add")))

    type_in(page.new_rate_value, "3,95")
    click(add_row, t("add"))
    pump(app)
    assert ExchangeRate.get(ExchangeRate.currency == "EUR").rate == "3.95"


def _add_transactions(app, rec, user):
    app.nav_buttons["transactions"].invoke()
    pump(app)
    page = app.current_frame
    from services.tag_service import get_transaction_tags
    from ui.pages.transactions import AddTransactionDialog

    # ── an expense with tags ──
    click(page, t("add_transaction"))
    d = window(app, AddTransactionDialog)
    type_in(d.amount_entry, "45,50")
    d.cat_var.set(category_key(d.cat_map, "expense"))
    type_in(d.note_entry, "Coffee")
    type_in(d.tags_entry, "#food #test")
    click(d, t("save_transaction"))
    pump(app)
    coffee = tx("Coffee")
    assert (coffee.type, coffee.amount_cents, coffee.currency) == ("expense", 4550, None)
    assert sorted(tg.name for tg in get_transaction_tags(coffee)) == ["food", "test"]

    # ── income ──
    click(page, t("add_transaction"))
    d = window(app, AddTransactionDialog)
    d.type_var.set("income")
    type_in(d.amount_entry, "5000")
    d.cat_var.set(category_key(d.cat_map, "income"))
    type_in(d.note_entry, "Salary")
    click(d, t("save_transaction"))
    pump(app)
    assert (tx("Salary").type, tx("Salary").amount_cents) == ("income", 500000)

    # ── recurring, started two months ago → the copies up to this month appear at once ──
    started = (date.today().replace(day=1) - timedelta(days=40)).replace(day=10)
    click(page, t("add_transaction"))
    d = window(app, AddTransactionDialog)
    type_in(d.amount_entry, "150")
    type_in(d.date_entry, started.strftime("%d.%m.%Y"))
    type_in(d.note_entry, "Gym")
    d.recurring_var.set(True)
    click(d, t("save_transaction"))
    pump(app)
    gym = Transaction.select().where(Transaction.note == "Gym").order_by(Transaction.date)
    assert [g.date.month for g in gym][-1] == date.today().month
    assert gym.count() == 3 and gym[0].is_recurring

    # ── in euro: the hint shows the converted amount while typing ──
    click(page, t("add_transaction"))
    d = window(app, AddTransactionDialog)
    field = d.amount_field
    field.currency_var.set("EUR")
    field._on_currency()                                 # what picking EUR in the menu does
    type_in(d.amount_entry, "20")
    field._refresh_hint()                                # what a key press does
    assert "79.00" in field.hint.cget("text")
    assert field.rate_entry.get() == "3.95"
    type_in(d.note_entry, "Vilnius dinner")
    click(d, t("save_transaction"))
    pump(app)
    dinner = tx("Vilnius dinner")
    assert (dinner.amount_cents, dinner.currency, dinner.original_amount_cents, dinner.exchange_rate) \
        == (7900, "EUR", 2000, "3.95")

    # ── wrong input: a message, the window stays open, nothing saved ──
    click(page, t("add_transaction"))
    d = window(app, AddTransactionDialog)
    for amount in ("abc", "0", "inf"):
        type_in(d.amount_entry, amount)
        expect_error(rec, t("invalid_amount"), lambda: click(d, t("save_transaction")))
    type_in(d.amount_entry, "10")
    type_in(d.date_entry, "31.02.2026")
    expect_error(rec, t("invalid_date"), lambda: click(d, t("save_transaction")))
    type_in(d.date_entry, date.today().strftime("%d.%m.%Y"))
    d.amount_field.currency_var.set("EUR")
    d.amount_field._on_currency()
    type_in(d.amount_field.rate_entry, "")
    expect_error(rec, t("rate_invalid"), lambda: click(d, t("save_transaction")))
    d.destroy()

    # ── Cmd+N from another page ──
    app.nav_buttons["dashboard"].invoke()
    pump(app)
    app._quick_add_transaction()
    d = window(app, AddTransactionDialog)
    type_in(d.amount_entry, "12.30")
    type_in(d.note_entry, "Bus")
    click(d, t("save_transaction"))
    pump(app)
    assert tx("Bus").amount_cents == 1230
    assert type(app.current_frame).__name__ == "TransactionsPage"   # shows the new entry


def _search_and_filters(app, rec):
    app.nav_buttons["transactions"].invoke()
    pump(app)
    page = app.current_frame

    type_in(page.search_entry, "coffee")
    page._on_search()
    assert [x.note for x in page._all_txs] == ["Coffee"]
    page._reset_filters()

    page._on_type_filter(t("income"))
    assert {x.type for x in page._all_txs} == {"income"}
    page._reset_filters()

    page._on_tag_filter("#food")
    assert [x.note for x in page._all_txs] == ["Coffee"]
    page._reset_filters()

    category = tx("Coffee").category
    key = next(k for k, c in page.cat_options.items() if c is not None and c.id == category.id)
    page._on_category_filter(key)
    assert "Coffee" in [x.note for x in page._all_txs]
    page._reset_filters()

    today = date.today().strftime("%d.%m.%Y")
    type_in(page.date_from_entry, today)
    type_in(page.date_to_entry, today)
    click(page, t("apply"))
    assert all(x.date == date.today() for x in page._all_txs)
    type_in(page.date_from_entry, "99.99.2026")
    expect_error(rec, "Invalid 'From' date. Use DD.MM.YYYY", lambda: click(page, t("apply")))
    page._reset_filters()
    assert len(page._all_txs) == Transaction.select().count()


def _edit_and_delete(app, rec, user):
    from services.currency_service import set_rate
    from ui.pages.transactions import EditTransactionDialog
    page = app.current_frame

    # ── amount and note of a plain purchase ──
    page._open_edit_dialog(tx("Coffee"))                 # the ✏️ button of the row
    e = window(app, EditTransactionDialog)
    assert e.amount_entry.get() == "45.50"
    type_in(e.amount_entry, "50")
    type_in(e.note_entry, "Coffee and cake")
    click(e, t("save_changes"))
    pump(app)
    assert tx("Coffee and cake").amount_cents == 5000

    # ── a euro purchase keeps its own rate, even after the saved rate changes ──
    set_rate(user, "EUR", "4.10")
    page = app.current_frame
    page._open_edit_dialog(tx("Vilnius dinner"))
    e = window(app, EditTransactionDialog)
    assert (e.amount_entry.get(), e.amount_field.currency_var.get(), e.amount_field.rate_entry.get()) \
        == ("20.00", "EUR", "3.95")
    type_in(e.amount_entry, "30")
    click(e, t("save_changes"))
    pump(app)
    assert (tx("Vilnius dinner").amount_cents, tx("Vilnius dinner").exchange_rate) == (11850, "3.95")

    # ── ...and can become a plain purchase again ──
    page = app.current_frame
    page._open_edit_dialog(tx("Vilnius dinner"))
    e = window(app, EditTransactionDialog)
    e.amount_field.currency_var.set(user.currency)
    e.amount_field._on_currency()
    type_in(e.amount_entry, "120")
    click(e, t("save_changes"))
    pump(app)
    assert (tx("Vilnius dinner").amount_cents, tx("Vilnius dinner").currency) == (12000, None)

    # ── wrong amount in Edit ──
    page = app.current_frame
    page._open_edit_dialog(tx("Bus"))
    e = window(app, EditTransactionDialog)
    type_in(e.amount_entry, "0")
    expect_error(rec, t("invalid_amount"), lambda: click(e, t("save_changes")))
    e.destroy()

    # ── delete ──
    page = app.current_frame
    page._delete(tx("Bus"))                              # the 🗑 button; "Yes" in the question
    pump(app)
    assert not Transaction.select().where(Transaction.note == "Bus").exists()


def _export_and_import(app, rec, user):
    from ui.pages.transactions import ImportCSVDialog
    page = app.current_frame
    count = Transaction.select().count()

    # ── CSV export: what is on screen ──
    rec.save_path = str(rec.tmp / "export.csv")
    click(page, t("export_csv"))
    with open(rec.save_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == count + 1
    assert rows[0][-3:] == [t("original_amount"), t("currency"), t("exchange_rate")]
    assert rec.infos[-1] == t("saved_to", count, rec.save_path)

    # ── PDF report ──
    rec.save_path = str(rec.tmp / "report.pdf")
    click(page, t("export_pdf"))
    assert os.path.getsize(rec.save_path) > 1000

    # ── import our own export back (Amount is column 3, Note column 4) ──
    rec.open_path = str(rec.tmp / "export.csv")
    click(page, t("import_csv"))
    d = window(app, ImportCSVDialog)
    click(d, t("choose_file"))
    pump(app)
    headers = d.preview["headers"]
    d.amount_col_var.set(f"3: {headers[3]}")
    d.note_col_var.set(f"4: {headers[4]}")
    d._guess_sign_mode()                                 # what picking the amount column does
    click(d, t("import_btn", d.preview["total_rows"]))
    pump(app)
    assert rec.infos[-1] == t("import_result", count, 0, 0)
    assert Transaction.select().count() == 2 * count

    # ── a statement of a euro card ──
    statement = rec.tmp / "euro.csv"
    statement.write_text("Date,Amount,Description\n02.11.2026,-20.00,Museum\n03.11.2026,-10.50,Taxi\n",
                         encoding="utf-8")
    rec.open_path = str(statement)
    page = app.current_frame
    click(page, t("import_csv"))
    d = window(app, ImportCSVDialog)
    click(d, t("choose_file"))
    pump(app)
    d.file_currency_var.set("EUR")
    d._on_file_currency()
    assert d.file_rate_entry.get() == "4.1"              # the saved rate, editable
    type_in(d.file_rate_entry, "")
    expect_error(rec, t("rate_invalid"), lambda: click(d, t("import_btn", 2)))
    type_in(d.file_rate_entry, "4")
    click(d, t("import_btn", 2))
    pump(app)
    museum, taxi = tx("Museum"), tx("Taxi")
    assert (museum.amount_cents, museum.currency, museum.original_amount_cents) == (8000, "EUR", 2000)
    assert (taxi.amount_cents, taxi.exchange_rate) == (4200, "4")


def _budget(app, rec):
    from ui.pages.budget import SetLimitDialog
    app.nav_buttons["budget"].invoke()
    pump(app)
    page = app.current_frame
    cafe = tx("Coffee and cake").category

    # a limit smaller than what was spent → "exceeded" (used by the notifications later)
    click(page, t("set_limit"))
    d = window(app, SetLimitDialog)
    d.cat_var.set(next(k for k, c in d.cat_map.items() if c.id == cafe.id))
    type_in(d.limit_entry, "abc")
    expect_error(rec, t("invalid_limit"), lambda: click(d, t("save_limit")))
    type_in(d.limit_entry, "40")
    click(d, t("save_limit"))
    pump(app)
    assert Budget.get(Budget.category == cafe.id).limit_cents == 4000

    # a second limit, then removed
    page = app.current_frame
    click(page, t("set_limit"))
    d = window(app, SetLimitDialog)
    other = next(k for k, c in d.cat_map.items() if c.id != cafe.id)
    d.cat_var.set(other)
    type_in(d.limit_entry, "100")
    click(d, t("save_limit"))
    pump(app)
    assert Budget.select().count() == 2
    page = app.current_frame
    page._delete_budget(Budget.get(Budget.category == d.cat_map[other].id))   # the ✕ of the row
    pump(app)
    assert Budget.select().count() == 1

    # nothing to copy from last month → a message
    page = app.current_frame
    click(page, t("copy_last_month"))
    assert rec.infos[-1] == t("no_prev_month")

    # another month and back
    page._on_month_change(months_list()[(date.today().month - 2) % 12])
    pump(app)
    page._on_month_change(months_list()[date.today().month - 1])
    pump(app)


def _goals(app, rec):
    from ui.pages.goals import AddGoalDialog, ContributeDialog
    app.nav_buttons["goals"].invoke()
    pump(app)
    page = app.current_frame

    click(page, t("new_goal"))
    d = window(app, AddGoalDialog)
    expect_error(rec, t("goal_name_required"), lambda: click(d, t("create_goal")))
    type_in(d.name_entry, "New laptop")
    type_in(d.amount_entry, "3500")
    type_in(d.deadline_entry, "31.12.2027")
    click(d, t("create_goal"))
    pump(app)
    goal = Goal.get(Goal.name == "New laptop")
    assert goal.target_cents == 350000

    page = app.current_frame
    click(page, t("contribute"))
    d = window(app, ContributeDialog)
    type_in(d.amount_entry, "500")
    click(d, t("contribute_btn"))
    pump(app)
    assert Goal.get_by_id(goal.id).current_cents == 50000

    page = app.current_frame
    page._archive(Goal.get_by_id(goal.id))               # the ✕ of the card; "Yes"
    pump(app)
    assert Goal.get_by_id(goal.id).status == "archived"


def _analytics(app):
    app.nav_buttons["analytics"].invoke()
    pump(app, 300)
    page = app.current_frame
    page._on_month_change(months_list()[(date.today().month - 2) % 12])
    pump(app, 300)
    page._on_month_change(months_list()[date.today().month - 1])
    pump(app, 300)


def _settings(app, rec, user):
    app.nav_buttons["settings"].invoke()
    pump(app)
    page = app.current_frame

    # ── profile (same currency → just saved) ──
    type_in(page.name_entry, "Nickolas")
    page.month_start_var.set("10")
    click(page, t("save_profile"))
    assert rec.infos[-1] == t("profile_saved")
    assert (User.get_by_id(user.id).name, User.get_by_id(user.id).month_start) == ("Nickolas", 10)

    # ── rates: change EUR in its row, add USD, delete it ──
    eur_row = row_of(page, "1 EUR =")
    type_in(find(eur_row, ctk.CTkEntry)[0], "4")
    click(eur_row, t("rate_save"))
    pump(app)
    assert ExchangeRate.get(ExchangeRate.currency == "EUR").rate == "4"
    page = app.current_frame
    page.new_rate_code.set("USD")
    type_in(page.new_rate_value, "3.70")
    click(page.new_rate_code.master, t("add"))
    pump(app)
    page = app.current_frame
    click(row_of(page, "1 USD ="), "×")
    pump(app)
    assert not ExchangeRate.select().where(ExchangeRate.currency == "USD").exists()

    # ── own category: add, archive ──
    page = app.current_frame
    expect_error(rec, t("cat_name_required"), lambda: click(page.new_cat_entry.master, t("add")))
    type_in(page.new_cat_entry, "Books")
    click(page.new_cat_entry.master, t("add"))
    pump(app)
    assert Category.get(Category.name == "Books").user_id == user.id
    page = app.current_frame
    click(page, t("archive_category"))
    pump(app)
    assert Category.get(Category.name == "Books").is_archived

    # ── theme and language ──
    page = app.current_frame
    page._change_theme(t("dark"))
    pump(app)
    page._change_theme(t("light"))
    pump(app)
    for language, code in (("Deutsch", "de"), ("English", "en")):
        app.current_frame._change_language(language)
        pump(app)
        assert User.get_by_id(user.id).language == code
        assert t("dashboard") in app.nav_buttons["dashboard"].cget("text")

    # ── backup, its folder, notifications ──
    from db.database import DB_PATH
    page = app.current_frame
    backups = os.path.join(os.path.dirname(DB_PATH), "backups")
    before = len(os.listdir(backups)) if os.path.isdir(backups) else 0
    click(page, t("backup_db"))
    assert len(os.listdir(backups)) == before + 1
    click(page, t("open_backup_folder"))
    assert rec.opened_folders == [backups]
    click(page, t("test_notifications"))
    assert len(rec.notifications) == 1 and rec.infos[-1].startswith(t("notifications_sent").format(1))


def _change_main_currency(app, rec):
    from services.currency_service import MODE_CONVERT
    from ui.components.change_currency_dialog import ChangeCurrencyDialog
    salary_before = tx("Salary").amount_cents
    museum_eur = tx("Museum").original_amount_cents

    # ── cancel: nothing changes ──
    page = app.current_frame
    page.currency_var.set("EUR")
    click(page, t("save_profile"))
    d = window(app, ChangeCurrencyDialog)
    click(d, t("cancel"))
    pump(app)
    assert page.currency_var.get() == "ILS" and User.get().currency == "ILS"

    # ── convert everything to euro with the saved rate (4) ──
    page.currency_var.set("EUR")
    click(page, t("save_profile"))
    d = window(app, ChangeCurrencyDialog)
    d.mode_var.set(MODE_CONVERT)
    d._on_mode()
    assert d.rate_entry.get() == "4"
    click(d, t("apply"))
    pump(app)
    assert User.get().currency == "EUR"
    assert tx("Salary").amount_cents == salary_before // 4          # 5000 ₪ → 1250 €
    museum = tx("Museum")
    assert (museum.amount_cents, museum.currency) == (museum_eur, None)   # paid in euro → exact

    # ── back to shekels, only the symbol ──
    page = app.current_frame
    page.currency_var.set("ILS")
    click(page, t("save_profile"))
    d = window(app, ChangeCurrencyDialog)
    click(d, t("apply"))                                  # "only the symbol" is the default
    pump(app)
    assert User.get().currency == "ILS"
    assert tx("Salary").amount_cents == salary_before // 4          # numbers untouched