"""Application settings + database backup (Partition A, Member A3).

The settings table itself is created by A1's migration.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from student_os.db import db_session, get_connection, get_db_path

DEFAULT_ATTENDANCE_THRESHOLD = 75.0


def get_setting(key, default=None, db_path=None):
    with db_session(db_path) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value, db_path=None):
    key = (key or "").strip()
    if not key:
        raise ValueError("Setting key is required.")
    with db_session(db_path) as conn:
        conn.execute(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, str(value)),
        )


def get_attendance_threshold(db_path=None):
    """Warning threshold as a percentage (default 75)."""
    raw = get_setting("attendance_threshold", db_path=db_path)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return DEFAULT_ATTENDANCE_THRESHOLD


def set_attendance_threshold(value, db_path=None):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("Attendance threshold must be a number between 0 and 100.")
    if not 0 <= number <= 100:
        raise ValueError("Attendance threshold must be between 0 and 100.")
    set_setting("attendance_threshold", number, db_path)
    return number


def backup_database(dest_dir=None, db_path=None):
    """Copy the live database to a timestamped file and return its path.

    Uses SQLite's backup API, which is safe even while the app has the file open.
    Default location: a 'backups' folder next to the database.
    """
    source_path = Path(db_path) if db_path else get_db_path()
    dest_dir = Path(dest_dir) if dest_dir else source_path.parent / "backups"
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target, n = dest_dir / f"student_os_{stamp}.db", 1
    while target.exists():  # two backups in the same second must not overwrite
        target = dest_dir / f"student_os_{stamp}_{n}.db"
        n += 1
    src = get_connection(db_path)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return str(target)
