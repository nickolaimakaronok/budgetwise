"""
db/database.py
Initializes the SQLite connection via Peewee.
The database lives in the app data folder (utils/platform_utils.app_data_dir),
so both the .app and terminal runs share the same data.
Up to version 1.8 it was ~/Documents/BudgetWise — db/data_move.py moves it.
"""

import os
from peewee import SqliteDatabase

from utils.platform_utils import app_data_dir

# macOS: ~/Library/Application Support/BudgetWise, Windows: %LOCALAPPDATA%,
# Linux: ~/.local/share — the same file for .app and python main.py
DB_DIR  = app_data_dir()
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
