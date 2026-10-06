"""Single-row student profile (Partition A, Member A1)."""
from student_os.db import db_session


def get_profile(db_path=None):
    """Return {'name', 'academic_session', 'semester'} or None if not set up yet."""
    with db_session(db_path) as conn:
        row = conn.execute(
            "SELECT name, academic_session, semester FROM student WHERE id = 1"
        ).fetchone()
    return dict(row) if row else None


def save_profile(name, academic_session="", semester="", db_path=None):
    """Create or update the one and only profile row. Returns the saved profile."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Name is required.")
    academic_session = (academic_session or "").strip()
    semester = (semester or "").strip()
    with db_session(db_path) as conn:
        conn.execute(
            """INSERT INTO student (id, name, academic_session, semester)
               VALUES (1, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name = excluded.name,
                   academic_session = excluded.academic_session,
                   semester = excluded.semester""",
            (name, academic_session, semester),
        )
    return {"name": name, "academic_session": academic_session, "semester": semester}
