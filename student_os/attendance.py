"""Attendance (Partition A, Member A3).

Percentage formula (project decision):

    attended   = Present + Late + Excused
    total      = Present + Late + Excused + Absent      (Excused IS part of the total)
    percentage = attended / total * 100

Change ATTENDED_STATUSES below to alter the formula in one place.
"""
from student_os.dates import parse_date, today_or
from student_os.db import db_session
from student_os.settings import get_attendance_threshold

STATUSES = ("Present", "Absent", "Late", "Excused")
ATTENDED_STATUSES = ("Present", "Late", "Excused")


def calculate_percentage(counts):
    """counts: dict with any of the four statuses. Returns float, or None if no sessions."""
    total = sum(counts.get(s, 0) for s in STATUSES)
    if total == 0:
        return None
    attended = sum(counts.get(s, 0) for s in ATTENDED_STATUSES)
    return attended / total * 100


def _summary(counts, threshold, **identity):
    counts = {s: counts.get(s, 0) for s in STATUSES}
    pct = calculate_percentage(counts)
    return {
        **identity,
        **{status.lower(): n for status, n in counts.items()},  # present, absent, late, excused
        "total": sum(counts.values()),
        "percentage": None if pct is None else round(pct, 1),
        # compared on the unrounded value, so 74.96% is not shown as "75.0, fine"
        "below_threshold": pct is not None and pct < threshold,
        "threshold": threshold,
    }


def record_attendance(course_id, date, status, today=None, db_path=None):
    """Record (or overwrite) a course's status for one date. Future dates are rejected."""
    day = parse_date(date, "Date")
    if day > today_or(today):
        raise ValueError("You can't record attendance for a future date.")
    status = str(status or "").strip().capitalize()
    if status not in STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(STATUSES)}.")
    with db_session(db_path) as conn:
        if conn.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone() is None:
            raise LookupError(f"Course {course_id} not found.")
        conn.execute(
            """INSERT INTO attendance (course_id, date, status) VALUES (?, ?, ?)
               ON CONFLICT(course_id, date) DO UPDATE SET status = excluded.status""",
            (course_id, day.isoformat(), status),
        )
    return {"course_id": course_id, "date": day.isoformat(), "status": status}


def delete_attendance(course_id, date, db_path=None):
    day = parse_date(date, "Date").isoformat()
    with db_session(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM attendance WHERE course_id = ? AND date = ?", (course_id, day))
        if cur.rowcount == 0:
            raise LookupError("No attendance record for that course and date.")


def get_attendance_records(course_id=None, db_path=None):
    """Individual records, newest first."""
    sql = """SELECT a.id, a.course_id, c.code AS course_code, a.date, a.status
             FROM attendance a JOIN courses c ON c.id = a.course_id"""
    params = ()
    if course_id is not None:
        sql += " WHERE a.course_id = ?"
        params = (course_id,)
    sql += " ORDER BY a.date DESC, a.id DESC"
    with db_session(db_path) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_all_summaries(db_path=None):
    """One summary per course (courses with no records included, percentage None)."""
    threshold = get_attendance_threshold(db_path)
    with db_session(db_path) as conn:
        courses = conn.execute("SELECT id, code, name FROM courses ORDER BY code").fetchall()
        rows = conn.execute(
            "SELECT course_id, status, COUNT(*) AS n FROM attendance GROUP BY course_id, status"
        ).fetchall()
    per_course = {}
    for r in rows:
        per_course.setdefault(r["course_id"], {})[r["status"]] = r["n"]
    return [
        _summary(per_course.get(c["id"], {}), threshold,
                 course_id=c["id"], course_code=c["code"], course_name=c["name"])
        for c in courses
    ]


def get_course_summary(course_id, db_path=None):
    for s in get_all_summaries(db_path):
        if s["course_id"] == course_id:
            return s
    raise LookupError(f"Course {course_id} not found.")


def get_courses_below_threshold(db_path=None):
    return [s for s in get_all_summaries(db_path) if s["below_threshold"]]


def get_overall_attendance(db_path=None):
    """Attendance across every recorded session of every course (Dashboard standing)."""
    threshold = get_attendance_threshold(db_path)
    with db_session(db_path) as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM attendance GROUP BY status").fetchall()
    return _summary({r["status"]: r["n"] for r in rows}, threshold)
