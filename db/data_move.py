"""
db/data_move.py
One-time move of the data folder from ~/Documents/BudgetWise (versions up
to 1.8) to the app data folder (utils/platform_utils.app_data_dir).

Order matters — at every moment a complete database exists somewhere:
  1. copy budget.db with the SQLite backup API (includes WAL data)
     into a temporary file next to the new location
  2. check the copy: integrity_check + the same number of rows in every table
  3. only then rename the temporary file to budget.db
  4. move the backups folder
  5. rename the old database to budget.db.moved and leave a note
Nothing is deleted. If step 1 or 2 fails, the old data is left untouched,
no new database appears, and the move is tried again on the next start.
"""

import logging
import os
import shutil
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

DB_NAME    = "budget.db"
MOVED_NAME = "budget.db.moved"
NOTE_NAME  = "WHERE_IS_MY_DATA.txt"

NOTE_TEXT = """\
BudgetWise moved its data to:
{new_dir}

The old database in this folder was renamed to {moved} on {stamp}.
BudgetWise no longer uses it — it is only a safety copy.

BudgetWise перенёс данные в папку, указанную выше.
Старая база здесь переименована в {moved} — это запасная копия,
программа её больше не использует.

BudgetWise hat seine Daten in den oben genannten Ordner verschoben.
Die alte Datenbank hier heißt jetzt {moved} — nur noch eine Sicherheitskopie.
"""


def _row_counts(con: sqlite3.Connection) -> dict[str, int]:
    tables = [row[0] for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    return {name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in tables}


def _is_empty_database(path: str) -> bool:
    """A budget.db without a single table — created by a stray connection, never used by the app."""
    if os.path.getsize(path) == 0:
        return True
    con = sqlite3.connect(path)
    try:
        return con.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0
    except sqlite3.DatabaseError:
        return False                       # not a database at all — don't touch it
    finally:
        con.close()


def _copy_and_check(src_path: str, dst_path: str) -> None:
    """Copies the database and raises if the copy is not identical in content."""
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
        check = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise sqlite3.DatabaseError(f"copy failed integrity_check: {check}")
        if _row_counts(src) != _row_counts(dst):
            raise sqlite3.DatabaseError("copy has a different number of rows")
    finally:
        dst.close()
        src.close()


def _move_backups(old_dir: str, new_dir: str) -> None:
    old_backups = os.path.join(old_dir, "backups")
    if not os.path.isdir(old_backups):
        return
    new_backups = os.path.join(new_dir, "backups")
    os.makedirs(new_backups, exist_ok=True)
    for name in os.listdir(old_backups):
        src = os.path.join(old_backups, name)
        dst = os.path.join(new_backups, name)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.move(src, dst)
    try:
        os.rmdir(old_backups)              # removed only if it is empty now
    except OSError:
        pass


def _retire_old_database(old_dir: str, new_dir: str) -> None:
    old_db = os.path.join(old_dir, DB_NAME)
    for suffix in ("", "-wal", "-shm"):    # keep the WAL file paired with its database
        if os.path.exists(old_db + suffix):
            os.replace(old_db + suffix, os.path.join(old_dir, MOVED_NAME + suffix))
    with open(os.path.join(old_dir, NOTE_NAME), "w", encoding="utf-8") as f:
        f.write(NOTE_TEXT.format(new_dir=new_dir, moved=MOVED_NAME,
                                 stamp=datetime.now().strftime("%Y-%m-%d %H:%M")))


def move_legacy_data(old_dir: str, new_dir: str) -> bool:
    """
    Moves budget.db and its backups from old_dir to new_dir.
    Returns True if data was moved, False if there was nothing to do.
    Raises if the copy can't be made or checked — the old data stays as it was.
    """
    if os.path.abspath(old_dir) == os.path.abspath(new_dir):
        return False
    old_db = os.path.join(old_dir, DB_NAME)
    new_db = os.path.join(new_dir, DB_NAME)
    if not os.path.exists(old_db):
        return False                       # fresh install, or already moved
    if os.path.exists(new_db) and not _is_empty_database(new_db):
        logger.warning(f"Both {old_db} and {new_db} exist — using {new_db}, the old one is left as is")
        return False

    os.makedirs(new_dir, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):    # an empty leftover and its WAL files must not stay
        if os.path.exists(new_db + suffix):
            os.remove(new_db + suffix)
    part = new_db + ".part"
    try:
        _copy_and_check(old_db, part)
    except Exception:
        if os.path.exists(part):
            os.remove(part)
        raise
    os.replace(part, new_db)               # budget.db appears only complete and checked
    logger.info(f"Database moved: {old_db} → {new_db}")

    # The data is safe in the new place now — problems below must not stop the app
    try:
        _move_backups(old_dir, new_dir)
        _retire_old_database(old_dir, new_dir)
    except OSError as e:
        logger.warning(f"Data moved, but tidying up {old_dir} failed: {e}")
    return True