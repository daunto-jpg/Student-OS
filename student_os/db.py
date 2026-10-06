"""Database layer for Student OS (Partition A, Member A1).

Responsibilities:
  - one place that opens SQLite connections (with foreign keys ON)
  - create the schema automatically on first run
  - upgrade the schema safely (versioned migrations, never drop data)

Nothing outside this package should write raw SQL against these tables
except the Partition A modules.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "student_os.db"

# ---------------------------------------------------------------------------
# Migrations
# Each entry is (version, [sql statements]). To change the schema later, ADD a
# new entry (e.g. version 2 with ALTER TABLE ...). Never edit an old entry.
# ---------------------------------------------------------------------------
MIGRATIONS = [
    (1, [
        """CREATE TABLE student (
            id               INTEGER PRIMARY KEY CHECK (id = 1),
            name             TEXT NOT NULL,
            academic_session TEXT NOT NULL DEFAULT '',
            semester         TEXT NOT NULL DEFAULT ''
        )""",
        """CREATE TABLE courses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            lecturer    TEXT NOT NULL DEFAULT '',
            credit_unit INTEGER NOT NULL CHECK (credit_unit > 0),
            venue       TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT ''
        )""",
        """CREATE TABLE timetable (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            day_of_week TEXT NOT NULL CHECK (day_of_week IN
                ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')),
            start_time  TEXT NOT NULL,   -- 'HH:MM' 24-hour
            end_time    TEXT NOT NULL,   -- 'HH:MM' 24-hour
            venue       TEXT NOT NULL DEFAULT '',
            CHECK (start_time < end_time)
        )""",
        """CREATE TABLE assignments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            title       TEXT NOT NULL,
            due_date    TEXT NOT NULL,   -- 'YYYY-MM-DD'
            status      TEXT NOT NULL DEFAULT 'Pending'
                        CHECK (status IN ('Pending','Completed')),
            priority    TEXT NOT NULL DEFAULT 'Medium'
                        CHECK (priority IN ('Low','Medium','High'))
        )""",
        # NOTE: overdue / due-today / due-soon are NOT stored; Python computes them.
        """CREATE TABLE attendance (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            date      TEXT NOT NULL,     -- 'YYYY-MM-DD'
            status    TEXT NOT NULL
                      CHECK (status IN ('Present','Absent','Late','Excused')),
            UNIQUE (course_id, date)
        )""",
        """CREATE TABLE notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id  INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            title      TEXT NOT NULL,
            content    TEXT NOT NULL DEFAULT '',
            tags       TEXT NOT NULL DEFAULT '',   -- comma-separated
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        # Key/value store. Table is created here (A1); functions belong to A3.
        """CREATE TABLE settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""",
        "INSERT INTO settings (key, value) VALUES ('attendance_threshold', '75')",
        "CREATE INDEX idx_timetable_day ON timetable(day_of_week)",
        "CREATE INDEX idx_assignments_due ON assignments(due_date)",
        "CREATE INDEX idx_attendance_course ON attendance(course_id)",
        "CREATE INDEX idx_notes_course ON notes(course_id)",
    ]),
]

LATEST_VERSION = MIGRATIONS[-1][0]


def get_db_path():
    """DB location: STUDENT_OS_DB env var if set, else data/student_os.db."""
    return Path(os.environ.get("STUDENT_OS_DB", DEFAULT_DB_PATH))


def get_connection(db_path=None):
    """Open a connection with foreign keys enforced and dict-like rows.

    SQLite ignores foreign keys unless this PRAGMA is set on EVERY connection,
    so always open connections through this function.
    """
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session(db_path=None):
    """Commit on success, roll back on error, always close."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_schema_version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]


def init_db(db_path=None):
    """Create or upgrade the database. Safe to call on every app start.

    Fresh file  -> runs every migration.
    Older file  -> runs only the migrations it hasn't had yet (data is kept).
    Each migration runs in one transaction, so a failure leaves the DB unchanged.
    Returns the schema version after upgrading.
    """
    conn = get_connection(db_path)
    try:
        current = get_schema_version(conn)
        for version, statements in MIGRATIONS:
            if version <= current:
                continue
            try:
                conn.execute("BEGIN")
                for sql in statements:
                    conn.execute(sql)
                conn.execute(f"PRAGMA user_version = {int(version)}")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return get_schema_version(conn)
    finally:
        conn.close()
      # Database module - Student
