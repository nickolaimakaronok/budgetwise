"""
db/database.py
Initializes the SQLite connection via Peewee.
Database is stored in ~/Documents/BudgetWise/ so both
the .app and terminal runs share the same data.
"""

import os
from peewee import SqliteDatabase

# Store database in user's Documents folder
# This ensures .app and python main.py use the same file
DB_DIR  = os.path.expanduser("~/Documents/BudgetWise")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "budget.db")

db = SqliteDatabase(
    DB_PATH,
    pragmas={
        "journal_mode": "wal",     # Better performance for concurrent writes
        "foreign_keys": 1,         # Enforce foreign key constraints
        "cache_size": -1024 * 32,  # 32MB cache
    },
)
