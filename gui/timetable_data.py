"""Plain-Python helpers for the Timetable screen (Partition B, Member B2).

No widgets and no SQL. Every "which class is next / which day is today"
decision is made by Partition A (timetable.get_next_class etc.); this file only
arranges the results for display and words them.
"""
from student_os import courses, timetable
from student_os.timetable import DAYS
from student_os.ui.dashboard_data import describe_next_class

NO_CLASSES_TEXT = "No classes scheduled yet."


def time_range(slot):
    return f"{slot['start_time']} - {slot['end_time']}"


def slot_title(slot):
    return f"{slot['course_code']}  {slot['course_name']}"


def course_choices(db_path=None):
    """[(label, id)] pairs for a FormDialog 'choice' field."""
    return [(f"{c['code']} - {c['name']}", c["id"]) for c in courses.list_courses(db_path)]


def editable_venue(slot, course):
    """Venue to pre-fill when editing a slot.

    Partition A reports the course venue for a slot whose own venue is blank.
    Pre-filling that would silently freeze it into the slot, so show it as blank.
    """
    if course is not None and slot["venue"] == course["venue"]:
        return ""
    return slot["venue"]


def build_week(now, db_path=None):
    """Everything the Timetable screen shows, as one dict.

    {'today': 'Wednesday', 'total': 5, 'next_class': slot | None, 'next_text': str,
     'days': [{'day': 'Monday', 'is_today': False, 'slots': [...]}, ... 7 entries]}
    """
    weekly = timetable.get_weekly_timetable(db_path)
    today = DAYS[now.weekday()]
    nxt = timetable.get_next_class(now=now, db_path=db_path)
    next_text = NO_CLASSES_TEXT
    if nxt:
        nxt = {**nxt, "when_text": describe_next_class(nxt)}
        next_text = f"Next class: {nxt['when_text']}  -  {nxt['course_code']} {nxt['course_name']}"
    days = [{"day": d, "is_today": d == today, "slots": weekly[d]} for d in DAYS]
    return {
        "today": today,
        "total": sum(len(d["slots"]) for d in days),
        "next_class": nxt,
        "next_text": next_text,
        "days": days,
    }
