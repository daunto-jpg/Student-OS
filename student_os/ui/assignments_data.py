"""Plain-Python helpers for the Assignments screen (Partition B, Member B3).

No widgets and no SQL. Overdue / due-today / due-soon are calculated by
Partition A (assignments.list_assignments); this file only filters and words them.
"""
from student_os import assignments
from student_os.ui.timetable_data import course_choices   # reused from B2

ALL = "All"
STATUS_FILTERS = (ALL, "Pending", "Completed")
PRIORITY_FILTERS = (ALL, "High", "Medium", "Low")


def course_filter_options(db_path=None):
    """[('All courses', None), ('CSC301 - Algorithms', 3), ...] for the filter menu."""
    return [("All courses", None)] + course_choices(db_path)


def load_assignments(course_id=None, status=ALL, priority=ALL, today=None, db_path=None):
    return assignments.list_assignments(
        course_id=course_id,
        status=None if status == ALL else status,
        priority=None if priority == ALL else priority,
        today=today, db_path=db_path)


def due_text(item):
    """'Due 2026-10-09 (in 2 days)' - completed items just show the date."""
    base = f"Due {item['due_date']}"
    if item["state"] == "Completed":
        return base
    n = item["days_left"]
    if n < 0:
        return f"{base} ({-n} day{'s' if n != -1 else ''} ago)"
    if n == 0:
        return f"{base} (today)"
    return f"{base} (in {n} day{'s' if n != 1 else ''})"


def summary_line(item):
    return f"{item['course_code']} {item['course_name']}  |  {due_text(item)}  |  {item['priority']} priority"


def count_text(n):
    return f"{n} assignment{'s' if n != 1 else ''}"


def empty_text(filtered=False):
    return ("No assignments match these filters." if filtered
            else "No assignments yet. Click Add assignment to create one.")
