"""
db/database.py
Initializes the SQLite connection via Peewee.
"""

import os
from peewee import SqliteDatabase

# Path to the database file — placed in the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "budget.db")

db = SqliteDatabase(
    DB_PATH,
    pragmas={
        "journal_mode": "wal",     # Better performance for concurrent writes
        "foreign_keys": 1,         # Enforce foreign key constraints
        "cache_size": -1024 * 32,  # 32MB cache
    },
)
