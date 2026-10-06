"""Course management (Partition A, Member A2).

Validation lives here so the GUI never has to re-check rules.
  - bad input          -> ValueError (message is safe to show the student)
  - course not found   -> LookupError
"""
import sqlite3

from student_os.db import db_session

_EDITABLE = {"code", "name", "lecturer", "credit_unit", "venue", "description"}


def _clean(code, name, credit_unit, lecturer, venue, description):
    code = (code or "").strip().upper()
    name = (name or "").strip()
    if not code:
        raise ValueError("Course code is required.")
    if not name:
        raise ValueError("Course name is required.")
    try:
        credit_unit = int(credit_unit)
    except (TypeError, ValueError):
        raise ValueError("Credit unit must be a whole number.")
    if credit_unit <= 0:
        raise ValueError("Credit unit must be greater than zero.")
    return {
        "code": code,
        "name": name,
        "credit_unit": credit_unit,
        "lecturer": (lecturer or "").strip(),
        "venue": (venue or "").strip(),
        "description": (description or "").strip(),
    }


def add_course(code, name, credit_unit, lecturer="", venue="", description="",
               db_path=None):
    """Add a course and return its new id."""
    c = _clean(code, name, credit_unit, lecturer, venue, description)
    try:
        with db_session(db_path) as conn:
            cur = conn.execute(
                """INSERT INTO courses (code, name, lecturer, credit_unit, venue, description)
                   VALUES (:code, :name, :lecturer, :credit_unit, :venue, :description)""",
                c,
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"A course with code {c['code']} already exists.")


def get_course(course_id, db_path=None):
    """Return the course as a dict, or None if it doesn't exist."""
    with db_session(db_path) as conn:
        row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    return dict(row) if row else None


def list_courses(db_path=None):
    """All courses, ordered by code."""
    with db_session(db_path) as conn:
        rows = conn.execute("SELECT * FROM courses ORDER BY code").fetchall()
    return [dict(r) for r in rows]


def search_courses(query, db_path=None):
    """Case-insensitive match on code, name, or lecturer. Blank query = all courses."""
    query = (query or "").strip()
    if not query:
        return list_courses(db_path)
    like = f"%{query}%"
    with db_session(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM courses
               WHERE code LIKE ? OR name LIKE ? OR lecturer LIKE ?
               ORDER BY code""",
            (like, like, like),
        ).fetchall()
    return [dict(r) for r in rows]


def update_course(course_id, **changes):
    """Update any of: code, name, lecturer, credit_unit, venue, description.

    Pass db_path=... as a keyword if needed. Returns the updated course dict.
    """
    db_path = changes.pop("db_path", None)
    unknown = set(changes) - _EDITABLE
    if unknown:
        raise ValueError(f"Cannot edit: {', '.join(sorted(unknown))}")
    current = get_course(course_id, db_path)
    if current is None:
        raise LookupError(f"Course {course_id} not found.")
    merged = {**current, **changes}
    c = _clean(merged["code"], merged["name"], merged["credit_unit"],
               merged["lecturer"], merged["venue"], merged["description"])
    try:
        with db_session(db_path) as conn:
            conn.execute(
                """UPDATE courses SET code=:code, name=:name, lecturer=:lecturer,
                   credit_unit=:credit_unit, venue=:venue, description=:description
                   WHERE id=:id""",
                {**c, "id": course_id},
            )
    except sqlite3.IntegrityError:
        raise ValueError(f"A course with code {c['code']} already exists.")
    return get_course(course_id, db_path)


def delete_course(course_id, db_path=None):
    """Delete a course AND everything linked to it (cascade)."""
    with db_session(db_path) as conn:
        cur = conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        if cur.rowcount == 0:
            raise LookupError(f"Course {course_id} not found.")


def count_linked_records(course_id, db_path=None):
    """How many rows a delete would remove, so the GUI can warn the student first."""
    with db_session(db_path) as conn:
        return {
            table: conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE course_id = ?", (course_id,)
            ).fetchone()[0]
            for table in ("timetable", "assignments", "attendance", "notes")
        }
