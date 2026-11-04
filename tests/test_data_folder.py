"""
tests/test_data_folder.py
Where the data lives on each OS, and the one-time move out of ~/Documents.
Everything happens in pytest's temporary folders — the real data is never touched.
"""

import os
import sqlite3
import sys

import pytest
from peewee import SqliteDatabase

import db.database
import db.migrations as migrations
from db.data_move import move_legacy_data, MOVED_NAME, NOTE_NAME
from models.models import ALL_MODELS, User, Transaction
from utils.platform_utils import app_data_dir


# ── Where the folder is ───────────────────────────────────────────────────────

@pytest.fixture
def no_custom_dir(monkeypatch):
    monkeypatch.delenv("BUDGETWISE_DATA_DIR", raising=False)


def test_mac_folder(monkeypatch, no_custom_dir):
    monkeypatch.setattr(sys, "platform", "darwin")
    home = os.path.expanduser("~")
    assert app_data_dir() == os.path.join(home, "Library", "Application Support", "BudgetWise")


def test_windows_folder(monkeypatch, no_custom_dir, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert app_data_dir() == os.path.join(str(tmp_path), "BudgetWise")


def test_linux_folder(monkeypatch, no_custom_dir, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    home = os.path.expanduser("~")
    assert app_data_dir() == os.path.join(home, ".local", "share", "BudgetWise")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert app_data_dir() == os.path.join(str(tmp_path), "BudgetWise")


def test_custom_folder_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("BUDGETWISE_DATA_DIR", str(tmp_path / "my data"))
    assert app_data_dir() == str(tmp_path / "my data")


def test_tests_never_use_the_real_folder():
    assert db.database.DB_PATH.startswith(os.environ["BUDGETWISE_DATA_DIR"])


# ── The move ──────────────────────────────────────────────────────────────────

def _make_db(path, notes):
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE t (note TEXT)")
    con.executemany("INSERT INTO t VALUES (?)", [(n,) for n in notes])
    con.commit()
    con.close()


def _notes(path):
    con = sqlite3.connect(str(path))
    try:
        return [row[0] for row in con.execute("SELECT note FROM t ORDER BY rowid")]
    finally:
        con.close()


@pytest.fixture
def old_dir(tmp_path):
    """~/Documents/BudgetWise as version 1.8 left it: database + backups."""
    folder = tmp_path / "Documents" / "BudgetWise"
    (folder / "backups").mkdir(parents=True)
    _make_db(folder / "budget.db", ["rent", "coffee", "Golan Telecom"])
    (folder / "backups" / "auto_backup_20261101_100000.db").write_bytes(b"auto")
    (folder / "backups" / "budget_backup_20261020_120000.db").write_bytes(b"manual")
    return folder


def test_moves_database_and_backups(old_dir, tmp_path):
    new_dir = tmp_path / "Application Support" / "BudgetWise"
    assert move_legacy_data(str(old_dir), str(new_dir)) is True

    assert _notes(new_dir / "budget.db") == ["rent", "coffee", "Golan Telecom"]
    assert sorted(os.listdir(new_dir / "backups")) == [
        "auto_backup_20261101_100000.db", "budget_backup_20261020_120000.db"]
    assert not (new_dir / "budget.db.part").exists()

    # the old database is kept under a new name, with a note next to it
    assert not (old_dir / "budget.db").exists()
    assert _notes(old_dir / MOVED_NAME) == ["rent", "coffee", "Golan Telecom"]
    assert str(new_dir) in (old_dir / NOTE_NAME).read_text(encoding="utf-8")


def test_second_start_does_nothing(old_dir, tmp_path):
    new_dir = tmp_path / "new"
    move_legacy_data(str(old_dir), str(new_dir))
    assert move_legacy_data(str(old_dir), str(new_dir)) is False
    assert _notes(new_dir / "budget.db") == ["rent", "coffee", "Golan Telecom"]


def test_fresh_install_does_nothing(tmp_path):
    new_dir = tmp_path / "new"
    assert move_legacy_data(str(tmp_path / "no such folder"), str(new_dir)) is False
    assert not new_dir.exists()


def test_existing_new_database_is_not_overwritten(old_dir, tmp_path):
    new_dir = tmp_path / "new"
    new_dir.mkdir()
    _make_db(new_dir / "budget.db", ["already here"])
    assert move_legacy_data(str(old_dir), str(new_dir)) is False
    assert _notes(new_dir / "budget.db") == ["already here"]
    assert (old_dir / "budget.db").exists()          # old one left as it was


def test_empty_new_database_does_not_block_the_move(old_dir, tmp_path):
    """An empty budget.db (a stray connection made it) is not "data already moved"."""
    new_dir = tmp_path / "new"
    new_dir.mkdir()
    sqlite3.connect(str(new_dir / "budget.db")).close()
    (new_dir / "budget.db-wal").write_bytes(b"stale")
    assert move_legacy_data(str(old_dir), str(new_dir)) is True
    assert _notes(new_dir / "budget.db") == ["rent", "coffee", "Golan Telecom"]
    assert not (new_dir / "budget.db-wal").exists()


def test_broken_old_database_is_left_untouched(tmp_path):
    old = tmp_path / "old"
    old.mkdir()
    garbage = b"this is not a database " * 100
    (old / "budget.db").write_bytes(garbage)
    new_dir = tmp_path / "new"

    with pytest.raises(sqlite3.DatabaseError):
        move_legacy_data(str(old), str(new_dir))

    assert (old / "budget.db").read_bytes() == garbage
    assert not (new_dir / "budget.db").exists()
    assert not (new_dir / "budget.db.part").exists()


# ── At app start (migrations.run) ─────────────────────────────────────────────

@pytest.fixture
def app_start(tmp_path, monkeypatch):
    """A real v1.8 user in old_dir; the app is about to start with an empty new_dir."""
    old_dir = tmp_path / "Documents" / "BudgetWise"
    old_dir.mkdir(parents=True)
    old_db = SqliteDatabase(str(old_dir / "budget.db"))
    old_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    old_db.create_tables(ALL_MODELS)
    user = User.create(name="Nick", currency="ILS")
    Transaction.create(user=user, type="expense", amount_cents=450000, note="rent")
    old_db.close()

    new_dir = tmp_path / "Application Support" / "BudgetWise"
    new_dir.mkdir(parents=True)                      # db/database.py creates it at import
    new_db = SqliteDatabase(str(new_dir / "budget.db"), pragmas={"journal_mode": "wal", "foreign_keys": 1})
    new_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    monkeypatch.setattr(migrations, "db", new_db)
    monkeypatch.setattr(db.database, "DB_PATH", str(new_dir / "budget.db"))
    monkeypatch.setattr(migrations, "legacy_data_dir", lambda: str(old_dir))
    monkeypatch.setattr(migrations, "app_data_dir", lambda: str(new_dir))
    yield old_dir, new_dir
    new_db.close()


def test_app_start_moves_data_before_the_backup(app_start, monkeypatch):
    old_dir, new_dir = app_start
    monkeypatch.delenv("BUDGETWISE_DATA_DIR", raising=False)
    migrations.run()

    assert User.get().name == "Nick"
    assert Transaction.get().note == "rent"
    backups = os.listdir(new_dir / "backups")
    assert len(backups) == 1                         # the startup backup is of the moved data
    con = sqlite3.connect(str(new_dir / "backups" / backups[0]))
    assert con.execute("SELECT note FROM transactions").fetchone()[0] == "rent"
    con.close()
    assert (old_dir / MOVED_NAME).exists()


def test_custom_folder_never_pulls_data_from_documents(app_start):
    old_dir, new_dir = app_start
    migrations.run()                                 # BUDGETWISE_DATA_DIR is set by conftest.py
    assert User.select().count() == 0
    assert (old_dir / "budget.db").exists()
    assert not (old_dir / MOVED_NAME).exists()


def test_database_elsewhere_never_pulls_data(app_start, monkeypatch):
    """Even without conftest.py: a database pointed somewhere else is not filled from ~/Documents."""
    old_dir, new_dir = app_start
    monkeypatch.delenv("BUDGETWISE_DATA_DIR", raising=False)
    monkeypatch.setattr(migrations, "app_data_dir", lambda: "/the/standard/folder")
    migrations.run()
    assert User.select().count() == 0
    assert (old_dir / "budget.db").exists()