"""
db/migrations.py
Creates tables on first run and seeds default system categories.
Run once via: python -m db.migrations
"""

import shutil
import os
from datetime import datetime
from db.database import db
from models.models import ALL_MODELS, Category


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
    """Creates a backup of the database before migration (if the file already exists)."""
    from db.database import DB_PATH
    if os.path.exists(DB_PATH):
        backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"budget_backup_{timestamp}.db")
        shutil.copy2(DB_PATH, backup_path)
        print(f"💾 Backup saved: {backup_path}")


def create_tables():
    """Creates all tables (skips existing ones)."""
    with db:
        db.create_tables(ALL_MODELS, safe=True)
    print("✅ Tables created")


def seed_categories():
    """Inserts system categories if they don't exist yet."""
    with db:
        existing = Category.select().where(Category.user.is_null()).count()
        if existing == 0:
            Category.insert_many(SYSTEM_CATEGORIES).execute()
            print(f"✅ Added {len(SYSTEM_CATEGORIES)} system categories")
        else:
            print(f"ℹ️  System categories already exist ({existing} found), skipping")


def run():
    backup_db()
    create_tables()
    seed_categories()
    print("🚀 Database is ready")


if __name__ == "__main__":
    run()
