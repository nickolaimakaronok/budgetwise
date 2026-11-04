"""
db/backup.py
Safe database backups.



Two kinds of backups live in the same folder:
  auto_backup_*.db    — made on every app start, only the newest AUTO_KEEP are kept
  budget_backup_*.db  — made by the user from Settings, never deleted automatically
"""

import logging
import os
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

AUTO_PREFIX   = "auto_backup_"
MANUAL_PREFIX = "budget_backup_"
AUTO_KEEP     = 10


def default_backup_dir(db_path: str) -> str:
    return os.path.join(os.path.dirname(db_path), "backups")


def _unique_path(folder: str, prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path  = os.path.join(folder, f"{prefix}{stamp}.db")
    n = 1
    while os.path.exists(path):
        path = os.path.join(folder, f"{prefix}{stamp}_{n}.db")
        n += 1
    return path


def create_backup(db_path: str, backup_dir: str | None = None,
                  prefix: str = MANUAL_PREFIX) -> str | None:
    """
    Copies the database (including un-checkpointed WAL data) to backup_dir.
    Returns the backup path, or None if the database file doesn't exist yet.
    """
    if not os.path.exists(db_path):
        return None

    backup_dir = backup_dir or default_backup_dir(db_path)
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = _unique_path(backup_dir, prefix)

    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(backup_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    logger.info(f"Backup saved: {backup_path}")
    return backup_path


def rotate_backups(backup_dir: str, prefix: str = AUTO_PREFIX,
                   keep: int = AUTO_KEEP) -> int:
    """Deletes all but the newest `keep` backups with the given prefix. Returns how many were removed."""
    if not os.path.isdir(backup_dir):
        return 0

    # Names carry the timestamp (plus a _N suffix on same-second clashes),
    # so reverse name order is newest-first.
    files = sorted(
        (f for f in os.listdir(backup_dir) if f.startswith(prefix) and f.endswith(".db")),
        reverse=True,
    )
    removed = 0
    for name in files[keep:]:
        try:
            os.remove(os.path.join(backup_dir, name))
            removed += 1
        except OSError as e:
            logger.warning(f"Could not remove old backup {name}: {e}")
    return removed


def create_auto_backup(db_path: str, backup_dir: str | None = None,
                       keep: int = AUTO_KEEP) -> str | None:
    """Startup backup: creates one and keeps only the newest `keep` auto backups."""
    path = create_backup(db_path, backup_dir, prefix=AUTO_PREFIX)
    if path:
        rotate_backups(os.path.dirname(path), AUTO_PREFIX, keep)
    return path