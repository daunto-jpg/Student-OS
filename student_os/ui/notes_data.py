"""Plain-Python helpers for the Notes screen (Partition B, Member B3).

No widgets and no SQL. Searching goes through Partition A (notes.py); the AI
buttons go through Partition C's Assistant, which is read-only and never raises
for a normal failure (offline, no key...) - it returns an AIResult instead.
"""
from student_os import notes
from student_os.ui.timetable_data import course_choices      # reused from B2

ALL_TAGS = "All tags"
# (button text, Assistant method name)
AI_ACTIONS = (("Explain", "explain_note"), ("Summarize", "summarize_note"),
              ("Quiz me", "revision_questions"))
AI_TITLES = {"explain_note": "Explanation", "summarize_note": "Summary",
             "revision_questions": "Revision questions"}


def course_filter_options(db_path=None):
    return [("All courses", None)] + course_choices(db_path)


def tag_options(course_id=None, db_path=None):
    return [ALL_TAGS] + notes.list_all_tags(course_id, db_path)


def load_notes(course_id=None, tag=ALL_TAGS, search="", db_path=None):
    return notes.list_notes(course_id=course_id, tag=None if tag == ALL_TAGS else tag,
                            search=search, db_path=db_path)


def preview(content, limit=140):
    text = " ".join((content or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def summary_line(note):
    parts = [f"{note['course_code']} {note['course_name']}"]
    if note["tags"]:
        parts.append("tags: " + ", ".join(note["tags"]))
    parts.append("edited " + (note["updated_at"] or "")[:10])
    return "  |  ".join(parts)


def count_text(n):
    return f"{n} note{'s' if n != 1 else ''}"


def empty_text(filtered=False):
    return ("No notes match these filters." if filtered
            else "No notes yet. Click Add note to write your first one.")


def run_ai(assistant, action, note_id):
    """Run one AI action on a note -> (window title, text to show).

    `action` is a method name from AI_ACTIONS. Failure text (offline, no key,
    empty note) is already student-friendly, so it is shown the same way.
    """
    if action not in AI_TITLES:
        raise ValueError(f"Unknown AI action: {action!r}")
    result = getattr(assistant, action)(note_id)
    text = result.text + (f"\n\n({result.notice})" if result.notice else "")
    return AI_TITLES[action], text
