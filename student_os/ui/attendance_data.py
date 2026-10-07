"""Plain-Python helpers for the Attendance screen (Partition B, Member B3).

No widgets and no SQL. Percentages and threshold warnings come from
Partition A (attendance.py); this file only words them.
"""
from student_os import attendance
from student_os.attendance import STATUSES      # Present / Absent / Late / Excused

RECENT_LIMIT = 15


def load_summaries(db_path=None):
    return attendance.get_all_summaries(db_path)


def load_recent(limit=RECENT_LIMIT, db_path=None):
    return attendance.get_attendance_records(db_path=db_path)[:limit]


def percent_text(summary):
    pct = summary["percentage"]
    return "No records" if pct is None else f"{pct:g}%"


def counts_line(summary):
    return (f"Present {summary['present']}  |  Late {summary['late']}  |  "
            f"Excused {summary['excused']}  |  Absent {summary['absent']}")


def warning_text(summary):
    return f"Below {summary['threshold']:g}%" if summary["below_threshold"] else ""


def default_date(now):
    return now.date().isoformat()


def record(course_id, date, status, now, db_path=None):
    """Raises ValueError for a bad / future date (Partition A's wording)."""
    return attendance.record_attendance(course_id, date, status, today=now, db_path=db_path)
