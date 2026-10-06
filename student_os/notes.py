"""Notes (Partition A, Member A3). Plain text, tied to a course, with tags + search."""
from student_os.db import db_session

_EDITABLE = {"course_id", "title", "content", "tags"}
_SELECT = """
    SELECT n.id, n.course_id, n.title, n.content, n.tags, n.created_at, n.updated_at,
           c.code AS course_code, c.name AS course_name
    FROM notes n JOIN courses c ON c.id = n.course_id
"""


def normalize_tags(tags):
    """'Exam, exam, Week 1' or ['Exam'] -> ['exam', 'week 1'] (lower-case, de-duplicated)."""
    if tags is None:
        return []
    parts = tags.split(",") if isinstance(tags, str) else list(tags)
    result = []
    for part in parts:
        tag = str(part).strip().lower()
        if tag and "," not in tag and tag not in result:
            result.append(tag)
    return result


def _escape(text):
    """Escape LIKE wildcards so searching for '100%' means a literal '%'."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like(text):
    return f"%{_escape(text)}%"


def _out(row):
    note = dict(row)
    note["tags"] = [t for t in note["tags"].split(",") if t]
    return note


def _require_course(conn, course_id):
    if conn.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone() is None:
        raise LookupError(f"Course {course_id} not found.")


def add_note(course_id, title, content="", tags=None, db_path=None):
    title = (title or "").strip()
    if not title:
        raise ValueError("Note title is required.")
    with db_session(db_path) as conn:
        _require_course(conn, course_id)
        cur = conn.execute(
            "INSERT INTO notes (course_id, title, content, tags) VALUES (?, ?, ?, ?)",
            (course_id, title, content or "", ",".join(normalize_tags(tags))),
        )
        return cur.lastrowid


def get_note(note_id, db_path=None):
    with db_session(db_path) as conn:
        row = conn.execute(_SELECT + " WHERE n.id = ?", (note_id,)).fetchone()
    return _out(row) if row else None


def update_note(note_id, **changes):
    """Edit any of: course_id, title, content, tags. Refreshes updated_at."""
    db_path = changes.pop("db_path", None)
    unknown = set(changes) - _EDITABLE
    if unknown:
        raise ValueError(f"Cannot edit: {', '.join(sorted(unknown))}")
    current = get_note(note_id, db_path)
    if current is None:
        raise LookupError(f"Note {note_id} not found.")
    merged = {**current, **changes}
    title = (merged["title"] or "").strip()
    if not title:
        raise ValueError("Note title is required.")
    with db_session(db_path) as conn:
        _require_course(conn, merged["course_id"])
        conn.execute(
            """UPDATE notes SET course_id=?, title=?, content=?, tags=?,
               updated_at = datetime('now') WHERE id=?""",
            (merged["course_id"], title, merged["content"] or "",
             ",".join(normalize_tags(merged["tags"])), note_id),
        )
    return get_note(note_id, db_path)


def delete_note(note_id, db_path=None):
    with db_session(db_path) as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        if cur.rowcount == 0:
            raise LookupError(f"Note {note_id} not found.")


def list_notes(course_id=None, tag=None, search=None, limit=None, db_path=None):
    """Filter by course, exact tag, and/or text search (title, content, tags).

    Most recently edited first.
    """
    where, params = [], []
    if course_id is not None:
        where.append("n.course_id = ?")
        params.append(course_id)
    if tag:
        wanted = normalize_tags(tag)
        if wanted:
            where.append("(',' || n.tags || ',') LIKE ? ESCAPE '\\'")
            params.append(f"%,{_escape(wanted[0])},%")
    if search and search.strip():
        pattern = _like(search.strip())
        where.append("(n.title LIKE ? ESCAPE '\\' OR n.content LIKE ? ESCAPE '\\' "
                     "OR n.tags LIKE ? ESCAPE '\\')")
        params.extend([pattern, pattern, pattern])
    sql = _SELECT + (" WHERE " + " AND ".join(where) if where else "")
    sql += " ORDER BY n.updated_at DESC, n.id DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    with db_session(db_path) as conn:
        return [_out(r) for r in conn.execute(sql, params).fetchall()]


def get_recent_notes(limit=5, db_path=None):
    """For the Dashboard."""
    return list_notes(limit=limit, db_path=db_path)


def list_all_tags(course_id=None, db_path=None):
    """Every tag in use (sorted), optionally for one course - for filter dropdowns."""
    sql, params = "SELECT tags FROM notes WHERE tags != ''", ()
    if course_id is not None:
        sql += " AND course_id = ?"
        params = (course_id,)
    with db_session(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return sorted({t for r in rows for t in r["tags"].split(",") if t})
