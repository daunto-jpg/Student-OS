"""Weekly timetable (Partition A, Member A2).

Times are stored as zero-padded 24-hour 'HH:MM' strings so that plain string
comparison orders them correctly. "Now" can be passed in (datetime) so the
today/next-class logic is testable and never depends on the real clock.
"""
import re
from datetime import datetime

from student_os.db import db_session

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_TIME_RE = re.compile(r"([01]\d|2[0-3]):[0-5]\d")

_SELECT = """
    SELECT t.id, t.course_id, t.day_of_week, t.start_time, t.end_time,
           COALESCE(NULLIF(t.venue, ''), c.venue) AS venue,
           c.code AS course_code, c.name AS course_name
    FROM timetable t JOIN courses c ON c.id = t.course_id
"""


def _validate(day, start, end):
    day = (day or "").strip().capitalize()
    if day not in DAYS:
        raise ValueError("Day must be a weekday name, e.g. 'Monday'.")
    for label, value in (("Start", start), ("End", end)):
        if not isinstance(value, str) or not _TIME_RE.fullmatch(value.strip()):
            raise ValueError(f"{label} time must be in 24-hour HH:MM format, e.g. 08:00.")
    start, end = start.strip(), end.strip()
    if start >= end:
        raise ValueError("Start time must be before end time.")
    return day, start, end


def _check_overlap(conn, day, start, end, ignore_id=None):
    row = conn.execute(
        """SELECT c.code, t.start_time, t.end_time
           FROM timetable t JOIN courses c ON c.id = t.course_id
           WHERE t.day_of_week = ? AND t.start_time < ? AND t.end_time > ?
             AND t.id != COALESCE(?, -1)""",
        (day, end, start, ignore_id),
    ).fetchone()
    if row:
        raise ValueError(
            f"This clashes with {row['code']} on {day} ({row['start_time']}-{row['end_time']})."
        )


def _require_course(conn, course_id):
    if conn.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone() is None:
        raise LookupError(f"Course {course_id} not found.")


def add_slot(course_id, day_of_week, start_time, end_time, venue="", db_path=None):
    """Add a class slot and return its id. Blank venue falls back to the course venue."""
    day, start, end = _validate(day_of_week, start_time, end_time)
    with db_session(db_path) as conn:
        _require_course(conn, course_id)
        _check_overlap(conn, day, start, end)
        cur = conn.execute(
            """INSERT INTO timetable (course_id, day_of_week, start_time, end_time, venue)
               VALUES (?, ?, ?, ?, ?)""",
            (course_id, day, start, end, (venue or "").strip()),
        )
        return cur.lastrowid


def get_slot(slot_id, db_path=None):
    with db_session(db_path) as conn:
        row = conn.execute(_SELECT + " WHERE t.id = ?", (slot_id,)).fetchone()
    return dict(row) if row else None


def update_slot(slot_id, day_of_week, start_time, end_time, venue="", db_path=None):
    """Replace a slot's day/times/venue (the course stays the same)."""
    day, start, end = _validate(day_of_week, start_time, end_time)
    with db_session(db_path) as conn:
        if conn.execute("SELECT 1 FROM timetable WHERE id = ?", (slot_id,)).fetchone() is None:
            raise LookupError(f"Timetable slot {slot_id} not found.")
        _check_overlap(conn, day, start, end, ignore_id=slot_id)
        conn.execute(
            """UPDATE timetable SET day_of_week=?, start_time=?, end_time=?, venue=?
               WHERE id=?""",
            (day, start, end, (venue or "").strip(), slot_id),
        )
    return get_slot(slot_id, db_path)


def delete_slot(slot_id, db_path=None):
    with db_session(db_path) as conn:
        cur = conn.execute("DELETE FROM timetable WHERE id = ?", (slot_id,))
        if cur.rowcount == 0:
            raise LookupError(f"Timetable slot {slot_id} not found.")


def get_classes_for_day(day_name, db_path=None):
    """Slots for one weekday, earliest first."""
    day = (day_name or "").strip().capitalize()
    if day not in DAYS:
        raise ValueError("Day must be a weekday name, e.g. 'Monday'.")
    with db_session(db_path) as conn:
        rows = conn.execute(
            _SELECT + " WHERE t.day_of_week = ? ORDER BY t.start_time", (day,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_weekly_timetable(db_path=None):
    """{'Monday': [...], ..., 'Sunday': [...]} - every day present, possibly empty."""
    return {day: get_classes_for_day(day, db_path) for day in DAYS}


def get_todays_classes(now=None, db_path=None):
    now = now or datetime.now()
    return get_classes_for_day(DAYS[now.weekday()], db_path)


def get_next_class(now=None, db_path=None):
    """The next class that STARTS after `now`, looking up to a week ahead.

    Returns the slot dict plus 'is_today' (bool) and 'days_until' (0-7),
    or None if the timetable is empty. A class already in progress is not "next".
    """
    now = now or datetime.now()
    today_idx = now.weekday()
    current_time = now.strftime("%H:%M")
    for offset in range(8):  # 0..7: day 7 is the same weekday next week
        day = DAYS[(today_idx + offset) % 7]
        for slot in get_classes_for_day(day, db_path):
            if offset == 0 and slot["start_time"] <= current_time:
                continue
            return {**slot, "is_today": offset == 0, "days_until": offset}
    return None
