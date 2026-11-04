"""
db/migrations.py
Creates tables on first run and seeds default system categories.
Run once via: python -m db.migrations
"""

from datetime import date
from db.database import db
from db.backup import create_auto_backup
from models.models import ALL_MODELS, Category, Transaction
import logging
logger = logging.getLogger(__name__)


# ── System categories (user=NULL, shared across all users) ───────────────────

SYSTEM_CATEGORIES = [
    # Expenses
    {"name": "Groceries",        "icon": "🛒", "color": "#16A34A", "type": "expense"},
    {"name": "Cafes & Dining",   "icon": "☕", "color": "#D97706", "type": "expense"},
    {"name": "Transport",        "icon": "🚇", "color": "#2563EB", "type": "expense"},
    {"name": "Housing & Bills",  "icon": "🏠", "color": "#7C3AED", "type": "expense"},
    {"name": "Health",           "icon": "💊", "color": "#DC2626", "type": "expense"},
    {"name": "Clothing",         "icon": "👕", "color": "#EC4899", "type": "expense"},
    {"name": "Entertainment",    "icon": "🎬", "color": "#F59E0B", "type": "expense"},
    {"name": "Sports",           "icon": "🏋️", "color": "#059669", "type": "expense"},
    {"name": "Subscriptions",    "icon": "📱", "color": "#0891B2", "type": "expense"},
    {"name": "Education",        "icon": "📚", "color": "#6366F1", "type": "expense"},
    {"name": "Travel",           "icon": "✈️", "color": "#0EA5E9", "type": "expense"},
    {"name": "Gifts",            "icon": "🎁", "color": "#F43F5E", "type": "expense"},
    {"name": "Other",            "icon": "📦", "color": "#64748B", "type": "expense"},
    # Income
    {"name": "Salary",           "icon": "💼", "color": "#16A34A", "type": "income"},
    {"name": "Freelance",        "icon": "💻", "color": "#2563EB", "type": "income"},
    {"name": "Side Job",         "icon": "🔧", "color": "#D97706", "type": "income"},
    {"name": "Investments",      "icon": "📈", "color": "#7C3AED", "type": "income"},
    {"name": "Other Income",     "icon": "💰", "color": "#64748B", "type": "income"},
]


def backup_db():
    """Backs up the DB before migrations: includes WAL data, keeps the last 10 auto backups."""
    from db.database import DB_PATH
    create_auto_backup(DB_PATH)


def create_tables():
    """Creates all tables (skips existing ones)."""
    with db:
        db.create_tables(ALL_MODELS, safe=True)
    logger.info("✅ Tables created")


def seed_categories():
    """Inserts system categories if they don't exist yet."""
    with db:
        existing = Category.select().where(Category.user.is_null()).count()
        if existing == 0:
            Category.insert_many(SYSTEM_CATEGORIES).execute()
            logger.info(f"✅ Added {len(SYSTEM_CATEGORIES)} system categories")
        else:
            logger.info(f"ℹ️  System categories already exist ({existing} found), skipping")


# Columns added after a table first shipped: (table, column, SQL type).
# Each one is added only if the table exists and the column is missing.
_NEW_COLUMNS = [
    # v1.4.0
    ("transactions", "is_recurring", "INTEGER DEFAULT 0"),
    # v1.7.0
    ("users", "language", "TEXT DEFAULT 'en'"),
    # v1.9.0 — recurring series: copies point to their template
    ("transactions", "recurring_parent_id",
     "INTEGER REFERENCES transactions (id) ON DELETE SET NULL"),
    ("transactions", "recurring_last_month", "DATE"),
]
# v1.8.0 — tags and transaction_tags are new TABLES,
# so create_tables(safe=True) handles them — no ALTER needed.


def _column_exists(table: str, column: str) -> bool:
    return any(c.name == column for c in db.get_columns(table))


def _add_missing_columns():
    """
    Adds new columns to existing tables.

    MUST run BEFORE create_tables(): for a new foreign-key column peewee also
    runs CREATE INDEX IF NOT EXISTS on it. If the column doesn't exist yet,
    SQLite treats the double-quoted name as a string literal and builds the
    index on a constant; adding the column afterwards leaves that index
    pointing at the wrong values ("database disk image is malformed").
    """
    tables = set(db.get_tables())
    for table, column, sql_type in _NEW_COLUMNS:
        if table in tables and not _column_exists(table, column):
            db.execute_sql(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
            logger.info(f"Migration: added {table}.{column}")


def _apply_data_migrations():
    """One-time data migrations, tracked with SQLite's built-in user_version."""
    version = db.execute_sql("PRAGMA user_version").fetchone()[0]
    if version < 1:
        with db.atomic():
            fixed = _migrate_recurring_series()
            db.execute_sql("PRAGMA user_version = 1")
        logger.info(f"Migration v1: recurring series rebuilt ({fixed} copies linked)")


def _first_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def _migrate_recurring_series() -> int:
    """
    Before v1.9.0 every auto-created copy was itself saved with
    is_recurring=True, so each month added another "template".
    Rebuild the series: rows the old code treated as the same transaction
    (same user, type, category, amount, note) form one series —
    the oldest stays the template, the rest become linked copies.
    Returns the number of copies that were relinked.
    """
    rows = list(
        Transaction.select()
        .where(Transaction.is_recurring == True)
        .order_by(Transaction.date, Transaction.id)
    )

    series: dict[tuple, list] = {}
    for tx in rows:
        key = (tx.user_id, tx.type, tx.category_id, tx.amount_cents, tx.note)
        series.setdefault(key, []).append(tx)

    relinked = 0
    for txs in series.values():
        template, copies = txs[0], txs[1:]
        last = max(txs, key=lambda t: t.date).date
        template.recurring_last_month = _first_of_month(last)
        template.save()
        for c in copies:
            c.is_recurring     = False
            c.recurring_parent = template
            c.save()
            relinked += 1
    return relinked


def run():
    backup_db()
    with db:
        _add_missing_columns()      # BEFORE create_tables — see docstring
    create_tables()
    with db:
        _apply_data_migrations()
    seed_categories()
    logger.info("🚀 Database is ready")


if __name__ == "__main__":
    run()