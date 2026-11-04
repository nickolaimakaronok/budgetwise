"""
db/migrations.py
Creates tables on first run and seeds default system categories.
Run once via: python -m db.migrations
"""

from db.database import db
from db.backup import create_auto_backup
from models.models import ALL_MODELS, Category
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


def _apply_migrations():
    """
    Safely adds new columns to existing tables.
    Each migration is wrapped in try/except — safe to run multiple times.
    If column already exists — OperationalError is raised and caught silently.
    """

    # v1.4.0 — add is_recurring to transaction table
    try:
        db.execute_sql(
            'ALTER TABLE transactions ADD COLUMN is_recurring INTEGER DEFAULT 0'
        )
        logger.info("Migration: added is_recurring column")
    except Exception:
        pass

    # v1.7.0 — add language to users table
    try:
        db.execute_sql(
            "ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'"
        )
        logger.info("Migration: added language column")
    except Exception:
        pass

    # v1.8.0 — tags and transaction_tags tables
    # Handled by create_tables(safe=True) above — no ALTER needed.
    # The Tag and TransactionTag models are in ALL_MODELS.


def run():
    backup_db()
    create_tables()
    _apply_migrations()
    seed_categories()
    logger.info("🚀 Database is ready")


if __name__ == "__main__":
    run()
