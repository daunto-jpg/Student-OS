"""Assignment tracker (Partition A, Member A3).

Overdue / due-today / due-soon are COMPUTED from today's date every time and
never stored, so they cannot go stale.
"""
from student_os.dates import parse_date, today_or
from student_os.db import db_session

PRIORITIES = ("Low", "Medium", "High")
STATUSES = ("Pending", "Completed")
DUE_SOON_DAYS = 3  # due in 1..3 days (not today) counts as "Due Soon"
_EDITABLE = {"course_id", "title", "due_date", "status", "priority"}

_SELECT = """
    SELECT a.id, a.course_id, a.title, a.due_date, a.status, a.priority,
           c.code AS course_code, c.name AS course_name
    FROM assignments a JOIN courses c ON c.id = a.course_id
"""
_ORDER = """ ORDER BY a.due_date,
    CASE a.priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, a.id"""


def get_assignment_state(due_date, status="Pending", today=None):
    """'Completed' | 'Overdue' | 'Due Today' | 'Due Soon' | 'Upcoming'."""
    if status == "Completed":
        return "Completed"
    days_left = (parse_date(due_date) - today_or(today)).days
    if days_left < 0:
        return "Overdue"
    if days_left == 0:
        return "Due Today"
    if days_left <= DUE_SOON_DAYS:
        return "Due Soon"
    return "Upcoming"


def _decorate(row, today):
    item = dict(row)
    item["state"] = get_assignment_state(item["due_date"], item["status"], today)
    item["days_left"] = (parse_date(item["due_date"]) - today_or(today)).days
    return item


def _clean(title, due_date, status, priority):
    title = (title or "").strip()
    if not title:
        raise ValueError("Assignment title is required.")
    status = str(status or "").strip().capitalize()
    priority = str(priority or "").strip().capitalize()
    if status not in STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(STATUSES)}.")
    if priority not in PRIORITIES:
        raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}.")
    return title, parse_date(due_date, "Due date").isoformat(), status, priority


def _require_course(conn, course_id):
    if conn.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone() is None:
        raise LookupError(f"Course {course_id} not found.")


def add_assignment(course_id, title, due_date, priority="Medium", status="Pending",
                   db_path=None):
    title, due, status, priority = _clean(title, due_date, status, priority)
    with db_session(db_path) as conn:
        _require_course(conn, course_id)
        cur = conn.execute(
            """INSERT INTO assignments (course_id, title, due_date, status, priority)
               VALUES (?, ?, ?, ?, ?)""",
            (course_id, title, due, status, priority),
        )
        return cur.lastrowid


def get_assignment(assignment_id, today=None, db_path=None):
    with db_session(db_path) as conn:
        row = conn.execute(_SELECT + " WHERE a.id = ?", (assignment_id,)).fetchone()
    return _decorate(row, today) if row else None


def update_assignment(assignment_id, **changes):
    """Edit any of: course_id, title, due_date, status, priority. Returns the result."""
    db_path = changes.pop("db_path", None)
    today = changes.pop("today", None)
    unknown = set(changes) - _EDITABLE
    if unknown:
        raise ValueError(f"Cannot edit: {', '.join(sorted(unknown))}")
    current = get_assignment(assignment_id, db_path=db_path)
    if current is None:
        raise LookupError(f"Assignment {assignment_id} not found.")
    merged = {**current, **changes}
    title, due, status, priority = _clean(
        merged["title"], merged["due_date"], merged["status"], merged["priority"])
    with db_session(db_path) as conn:
        _require_course(conn, merged["course_id"])
        conn.execute(
            """UPDATE assignments SET course_id=?, title=?, due_date=?, status=?, priority=?
               WHERE id=?""",
            (merged["course_id"], title, due, status, priority, assignment_id),
        )
    return get_assignment(assignment_id, today, db_path)


def mark_complete(assignment_id, today=None, db_path=None):
    return update_assignment(assignment_id, status="Completed", today=today, db_path=db_path)


def delete_assignment(assignment_id, db_path=None):
    with db_session(db_path) as conn:
        cur = conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
        if cur.rowcount == 0:
            raise LookupError(f"Assignment {assignment_id} not found.")


def list_assignments(course_id=None, status=None, priority=None, state=None,
                     today=None, db_path=None):
    """Filter by course / status / priority (SQL) and computed state (Python).

    Sorted by due date, then priority (High first).
    """
    where, params = [], []
    if course_id is not None:
        where.append("a.course_id = ?")
        params.append(course_id)
    if status:
        where.append("a.status = ?")
        params.append(str(status).capitalize())
    if priority:
        where.append("a.priority = ?")
        params.append(str(priority).capitalize())
    sql = _SELECT + (" WHERE " + " AND ".join(where) if where else "") + _ORDER
    with db_session(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    items = [_decorate(r, today) for r in rows]
    if state:
        items = [i for i in items if i["state"].lower() == str(state).lower()]
    return items


def get_pending_assignments(today=None, db_path=None):
    """Everything not completed (includes overdue) - for the Dashboard."""
    return list_assignments(status="Pending", today=today, db_path=db_path)


def get_overdue_assignments(today=None, db_path=None):
    return list_assignments(state="Overdue", today=today, db_path=db_path)
