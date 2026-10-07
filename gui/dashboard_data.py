"""Everything the Dashboard shows, gathered into one plain dict (Partition B, B1).

No widgets here and no SQL: this only calls Partition A functions and shapes
their results. Because it needs no GUI library, it is fully unit-tested.

`now` is injectable (a datetime) so tests never depend on the real clock -
the same convention Partition A uses.
"""
from datetime import datetime

from student_os import assignments, attendance, courses, notes, profile, timetable

RECENT_NOTES = 5
MAX_ASSIGNMENTS_SHOWN = 6


def greeting_for(hour):
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 22:
        return "Good evening"
    return "Hello"


def class_status(slot, now_hhmm):
    """'Upcoming' | 'Ongoing' | 'Finished' for a timetable slot (HH:MM strings compare correctly)."""
    if now_hhmm < slot["start_time"]:
        return "Upcoming"
    if now_hhmm < slot["end_time"]:
        return "Ongoing"
    return "Finished"


def describe_next_class(slot):
    """Human wording for the next-class card, e.g. 'Today at 14:00' / 'Tomorrow at 08:00'."""
    days_until = slot["days_until"]
    if days_until == 0:
        return f"Today at {slot['start_time']}"
    if days_until == 1:
        return f"Tomorrow at {slot['start_time']}"
    if days_until >= 7:
        return f"Next {slot['day_of_week']} at {slot['start_time']}"
    return f"{slot['day_of_week']} at {slot['start_time']}"


def describe_days_left(days_left):
    """-2 -> 'overdue by 2 days', 0 -> 'due today', 1 -> 'due tomorrow', 5 -> 'due in 5 days'."""
    if days_left < 0:
        n = -days_left
        return f"overdue by {n} day{'s' if n != 1 else ''}"
    if days_left == 0:
        return "due today"
    if days_left == 1:
        return "due tomorrow"
    return f"due in {days_left} days"


def attendance_standing(overall):
    """Short label for the dashboard tile, from attendance.get_overall_attendance()."""
    if overall["percentage"] is None:
        return "No records yet"
    return "Below target" if overall["below_threshold"] else "On track"


def build_dashboard(now=None, db_path=None):
    """Collect the whole dashboard. Returns a dict with these keys:

    student_name, greeting, date_text, course_count,
    todays_classes   [slot + 'status'],
    next_class       slot + 'when_text'  (or None),
    assignments      {'items': [...], 'pending', 'overdue', 'due_today', 'due_soon'},
    attendance       {'overall': summary, 'standing': str, 'below': [summaries]},
    recent_notes     [note + 'updated_date']
    """
    now = now or datetime.now()
    today = now.date()
    now_hhmm = now.strftime("%H:%M")

    prof = profile.get_profile(db_path)
    name = prof["name"] if prof else ""

    classes = [
        {**slot, "status": class_status(slot, now_hhmm)}
        for slot in timetable.get_todays_classes(now=now, db_path=db_path)
    ]

    nxt = timetable.get_next_class(now=now, db_path=db_path)
    if nxt:
        nxt = {**nxt, "when_text": describe_next_class(nxt)}

    pending = assignments.get_pending_assignments(today=today, db_path=db_path)
    shown = [{**a, "due_text": describe_days_left(a["days_left"])}
             for a in pending[:MAX_ASSIGNMENTS_SHOWN]]
    count = lambda state: sum(1 for a in pending if a["state"] == state)  # noqa: E731

    overall = attendance.get_overall_attendance(db_path=db_path)

    recent = [{**n, "updated_date": (n["updated_at"] or "")[:10]}
              for n in notes.get_recent_notes(limit=RECENT_NOTES, db_path=db_path)]

    return {
        "student_name": name,
        "greeting": greeting_for(now.hour) + (f", {name.split()[0]}" if name else ""),
        "date_text": now.strftime("%A, %d %B %Y"),
        "course_count": len(courses.list_courses(db_path)),
        "todays_classes": classes,
        "next_class": nxt,
        "assignments": {
            "items": shown,
            "pending": len(pending),
            "overdue": count("Overdue"),
            "due_today": count("Due Today"),
            "due_soon": count("Due Soon"),
        },
        "attendance": {
            "overall": overall,
            "standing": attendance_standing(overall),
            "below": attendance.get_courses_below_threshold(db_path=db_path),
        },
        "recent_notes": recent,
    }
