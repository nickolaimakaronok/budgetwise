"""
tests/test_backup.py
Backups must include data still in the WAL file, and auto backups must rotate.
Run with: python -m pytest tests/test_backup.py -v
"""

import os
import sqlite3

from db.backup import create_backup, create_auto_backup, AUTO_PREFIX, MANUAL_PREFIX


def _wal_db_with_rows(path, n=20):
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=wal")
    con.execute("CREATE TABLE t (x INTEGER)")
    con.commit()
    # A second open connection (like the notification thread)
    # keeps SQLite from moving the WAL data into the main file.
    reader = sqlite3.connect(path)
    reader.execute("SELECT 1").fetchall()
    for i in range(n):
        con.execute("INSERT INTO t VALUES (?)", (i,))
    con.commit()
    return con, reader


def test_backup_contains_wal_data(tmp_path):
    db_path = str(tmp_path / "budget.db")
    con, reader = _wal_db_with_rows(db_path)
    try:
        assert os.path.getsize(db_path + "-wal") > 0       # data really sits in the WAL
        backup = create_backup(db_path)
        rows = sqlite3.connect(backup).execute("SELECT COUNT(*) FROM t").fetchone()[0]
        assert rows == 20
    finally:
        reader.close()
        con.close()


def test_backup_of_missing_db_returns_none(tmp_path):
    assert create_backup(str(tmp_path / "nope.db")) is None


def test_auto_backups_rotated_manual_kept(tmp_path):
    db_path = str(tmp_path / "budget.db")
    sqlite3.connect(db_path).close()
    create_backup(db_path)                       # one manual backup
    for _ in range(13):
        create_auto_backup(db_path, keep=10)
    files = os.listdir(tmp_path / "backups")
    assert len([f for f in files if f.startswith(AUTO_PREFIX)]) == 10
    assert len([f for f in files if f.startswith(MANUAL_PREFIX)]) == 1