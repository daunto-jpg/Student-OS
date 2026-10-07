"""Plain-Python helpers for the Courses screen (Partition B, Member B2).

No widgets and no SQL: only wording and calls into Partition A, so it is fully
unit-tested without a display.
"""
from student_os import courses

_LINKED_LABELS = (          # (key from courses.count_linked_records, singular, plural)
    ("timetable", "class slot", "class slots"),
    ("assignments", "assignment", "assignments"),
    ("attendance", "attendance record", "attendance records"),
    ("notes", "note", "notes"),
)


def credit_text(units):
    return f"{units} credit unit{'s' if units != 1 else ''}"


def course_summary(course):
    """'Dr Musa  |  LT1  |  3 credit units' - blank parts are left out."""
    parts = [course["lecturer"], course["venue"], credit_text(course["credit_unit"])]
    return "  |  ".join(p for p in parts if p)


def load_courses(query="", db_path=None):
    """Courses matching the search box (a blank query returns every course)."""
    return courses.search_courses(query, db_path)


def count_text(shown, query=""):
    if query:
        return f"{shown} match{'es' if shown != 1 else ''}"
    return f"{shown} course{'s' if shown != 1 else ''}"


def empty_text(query=""):
    if query:
        return f'No courses match "{query}".'
    return "No courses yet. Click Add course to create your first one."


def delete_warning(course, counts):
    """The message for the delete confirmation, naming exactly what will be lost.

    `counts` is the dict from courses.count_linked_records().
    """
    head = f"Delete {course['code']} - {course['name']}?"
    lost = []
    for key, singular, plural in _LINKED_LABELS:
        n = counts.get(key, 0)
        if n:
            lost.append(f"{n} {singular if n == 1 else plural}")
    if not lost:
        return head + "\n\nNothing else is linked to this course."
    return (head + "\n\nThis will also permanently delete: " + ", ".join(lost)
            + ".\nThis cannot be undone.")
