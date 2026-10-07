"""Dashboard data helpers (Partition B1).

Keeps presentation-friendly wording in Partition B while using Partition A
as the source of truth for all academic data and date/status calculations.
"""
from datetime import datetime

from student_os import assignments, attendance, courses, notes, profile, timetable

MAX_ASSIGNMENTS_SHOWN = 8
RECENT_NOTES = 5


def greeting_for(hour):
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 23:
        return "Good evening"
    return "Hello"


def describe_days_left(days):
    if days < 0:
        n = abs(days)
        return f"overdue by {n} day" if n == 1 else f"overdue by {n} days"
    if days == 0:
        return "due today"
    if days == 1:
        return "due tomorrow"
    return f"due in {days} days"


def class_status(slot, current_time):
    if current_time < slot["start_time"]:
        return "Upcoming"
    if current_time < slot["end_time"]:
        return "Ongoing"
    return "Finished"


def describe_next_class(slot):
    days_until = slot.get("days_until")
    if days_until == 0:
        prefix = "Today"
    elif days_until == 1:
        prefix = "Tomorrow"
    elif days_until == 7:
        prefix = f"Next {slot['day_of_week']}"
    else:
        prefix = slot["day_of_week"]
    return f"{prefix} at {slot['start_time']}"


def build_dashboard(now=None, db_path=None):
    now = now or datetime.now()
    prof = profile.get_profile(db_path) or {}
    first_name = prof.get("name", "").split()[0] if prof.get("name") else ""
    greeting = greeting_for(now.hour)
    if first_name:
        greeting += f", {first_name}"

    todays_classes = timetable.get_todays_classes(now=now, db_path=db_path)
    todays_classes = [
        {**slot, "status": class_status(slot, now.strftime("%H:%M"))}
        for slot in todays_classes
    ]

    next_class = timetable.get_next_class(now=now, db_path=db_path)
    if next_class:
        next_class = {**next_class, "when_text": describe_next_class(next_class)}

    pending_items = assignments.get_pending_assignments(today=now.date(), db_path=db_path)
    for item in pending_items:
        item["due_text"] = describe_days_left(item["days_left"])

    overdue = sum(i["state"] == "Overdue" for i in pending_items)
    due_today = sum(i["state"] == "Due Today" for i in pending_items)
    due_soon = sum(i["state"] == "Due Soon" for i in pending_items)

    overall = attendance.get_overall_attendance(db_path=db_path)
    standing = "No records yet"
    if overall["percentage"] is not None:
        standing = "Below target" if overall["below_threshold"] else "On target"

    return {
        "student_name": prof.get("name", ""),
        "greeting": greeting,
        "date_text": now.strftime("%A, %d %B %Y"),
        "course_count": len(courses.list_courses(db_path)),
        "todays_classes": todays_classes,
        "next_class": next_class,
        "assignments": {
            "items": pending_items[:MAX_ASSIGNMENTS_SHOWN],
            "pending": len(pending_items),
            "overdue": overdue,
            "due_today": due_today,
            "due_soon": due_soon,
        },
        "attendance": {
            "overall": overall,
            "standing": standing,
            "below": attendance.get_courses_below_threshold(db_path=db_path),
        },
        "recent_notes": notes.get_recent_notes(limit=RECENT_NOTES, db_path=db_path),
    }
