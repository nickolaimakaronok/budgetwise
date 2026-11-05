"""
tests/test_migrations.py
Upgrading a real v1.8.0 database file to the current schema.

Regression: adding the recurring_parent_id column AFTER create_tables()
left a broken index (SQLite built it on the not-yet-existing column as a
string literal) and the database reported "disk image is malformed".
Run with: python -m pytest tests/test_migrations.py -v
"""

import sqlite3

import pytest
from peewee import SqliteDatabase

import db.database
import db.migrations as migrations
from models.models import ALL_MODELS, Transaction, User

V180_SCHEMA = """
CREATE TABLE "users" ("id" INTEGER NOT NULL PRIMARY KEY, "name" TEXT NOT NULL, "password_hash" TEXT NOT NULL, "currency" TEXT NOT NULL, "month_start" INTEGER NOT NULL, "language" TEXT NOT NULL, "created_at" DATETIME NOT NULL);
CREATE TABLE "categories" ("id" INTEGER NOT NULL PRIMARY KEY, "user_id" INTEGER, "name" TEXT NOT NULL, "icon" TEXT NOT NULL, "color" TEXT NOT NULL, "type" TEXT NOT NULL, "is_archived" INTEGER NOT NULL, FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE);
CREATE INDEX "category_user_id" ON "categories" ("user_id");
CREATE TABLE "transactions" ("id" INTEGER NOT NULL PRIMARY KEY, "user_id" INTEGER NOT NULL, "type" TEXT NOT NULL, "amount_cents" INTEGER NOT NULL, "category_id" INTEGER, "date" DATE NOT NULL, "note" TEXT NOT NULL, "created_at" DATETIME NOT NULL, "is_recurring" INTEGER NOT NULL, FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE, FOREIGN KEY ("category_id") REFERENCES "categories" ("id") ON DELETE SET NULL);
CREATE INDEX "transaction_user_id" ON "transactions" ("user_id");
CREATE INDEX "transaction_category_id" ON "transactions" ("category_id");
"""


@pytest.fixture
def old_db(tmp_path, monkeypatch):
    """A v1.8.0 database file with legacy recurring rows (every copy marked recurring)."""
    path = str(tmp_path / "budget.db")
    con = sqlite3.connect(path)
    con.executescript(V180_SCHEMA)
    con.execute("INSERT INTO users VALUES (1, 'Nick', '', 'ILS', 1, 'ru', '2026-05-01 10:00:00')")
    for i, d in enumerate(["2026-05-30", "2026-06-30", "2026-07-31"], start=1):
        con.execute("INSERT INTO transactions VALUES (?, 1, 'expense', 450000, NULL, ?, 'rent', "
                    "'2026-05-01 10:00:00', 1)", (i, d))
    con.execute("INSERT INTO transactions VALUES (4, 1, 'expense', 100, NULL, '2026-06-02', 'coffee', "
                "'2026-05-01 10:00:00', 0)")
    con.commit()
    con.close()

    file_db = SqliteDatabase(path, pragmas={"journal_mode": "wal", "foreign_keys": 1})
    file_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    monkeypatch.setattr(migrations, "db", file_db)
    monkeypatch.setattr(db.database, "DB_PATH", path)
    yield path
    file_db.close()


def test_upgrade_keeps_database_healthy(old_db):
    migrations.run()
    migrations.run()          # running again is a no-op
    con = sqlite3.connect(old_db)
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    cols = {row[1] for row in con.execute("PRAGMA table_info(transactions)")}
    assert {"recurring_parent_id", "recurring_last_month"} <= cols
    assert con.execute("PRAGMA user_version").fetchone()[0] == 1


def test_upgrade_rebuilds_recurring_series(old_db):
    from services.transaction_service import create_recurring_for_month, get_recurring_transactions
    migrations.run()
    user = User.get()
    templates = get_recurring_transactions(user)
    assert [t.id for t in templates] == [1]
    assert {t.id for t in Transaction.select().where(Transaction.recurring_parent == 1)} == {2, 3}
    assert create_recurring_for_month(user, 2026, 7) == 0
    assert create_recurring_for_month(user, 2026, 8) == 1
    assert Transaction.select().order_by(Transaction.date.desc()).first().date.isoformat() == "2026-08-30"


def test_upgrade_makes_a_backup(old_db, tmp_path):
    migrations.run()
    backups = list((tmp_path / "backups").iterdir())
    assert len(backups) == 1
    con = sqlite3.connect(str(backups[0]))
    assert con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 4





def test_upgrade_adds_currency_columns_and_rates_table(old_db):
    """A 1.x/2.0 database gets the multi-currency columns; old rows stay in the main currency."""
    migrations.run()
    con = sqlite3.connect(old_db)
    cols = {row[1] for row in con.execute("PRAGMA table_info(transactions)")}
    assert {"currency", "original_amount_cents", "exchange_rate"} <= cols
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "exchange_rates" in tables
    assert con.execute("SELECT COUNT(*) FROM transactions WHERE currency IS NOT NULL").fetchone()[0] == 0
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"