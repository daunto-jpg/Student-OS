"""Context builder (Partition C, Member C2).

Collects ONLY the data a given AI request needs and turns it into plain text.
It calls the Partition A modules (read functions only) - no SQL here, and
nothing is ever written. Every date, deadline state and attendance percentage
in the text is calculated by Python, so Gemini never has to work them out.

`now` (a datetime) is injectable so tests never depend on the real clock.
"""
from datetime import datetime

from student_os import (
    assignments, attendance, courses, notes, profile, timetable,
)

MAX_NOTE_CHARS = 12000
MAX_PENDING_SHOWN = 25
MAX_NOTE_TITLES = 10
TOPICS = ("courses", "timetable", "assignments", "attendance", "notes")


def build_note_context(note_id, db_path=None):
    note = notes.get_note(note_id, db_path)
    if note is None:
        raise LookupError(f"Note {note_id} not found.")
    content = note["content"] or ""
    return {
        "note_id": note["id"], "course_code": note["course_code"],
        "course_name": note["course_name"], "title": note["title"],
        "tags": note["tags"], "content": content[:MAX_NOTE_CHARS],
        "truncated": len(content) > MAX_NOTE_CHARS,
        "original_length": len(content),
    }


def _days_phrase(days_left):
    if days_left < 0:
        n = -days_left
        return f"overdue by {n} day{'s' if n != 1 else ''}"
    if days_left == 0:
        return "due today"
    if days_left == 1:
        return "due tomorrow"
    return f"due in {days_left} days"


def _header(now, db_path):
    lines = [f"Current date and time: {now.strftime('%A, %d %B %Y, %H:%M')}"]
    prof = profile.get_profile(db_path)
    if prof:
        first = prof["name"].split()[0]
        lines.append(f"Student: {first}")
        extra = ", ".join(p for p in (prof["academic_session"], prof["semester"]) if p)
        if extra:
            lines.append(f"Session: {extra}")
    return "\n".join(lines)


def _section_courses(now, db_path):
    items = courses.list_courses(db_path)
    if not items:
        return "No courses have been added yet."
    out = []
    for c in items:
        bits = [f"{c['code']} - {c['name']}", f"{c['credit_unit']} credit unit(s)"]
        if c["lecturer"]:
            bits.append(f"lecturer: {c['lecturer']}")
        if c["venue"]:
            bits.append(f"venue: {c['venue']}")
        out.append(" | ".join(bits))
    return "\n".join(out)


def _slot_line(slot):
    venue = f" ({slot['venue']})" if slot["venue"] else ""
    return (f"{slot['start_time']}-{slot['end_time']} "
            f"{slot['course_code']} {slot['course_name']}{venue}")


def _section_timetable(now, db_path):
    week = timetable.get_weekly_timetable(db_path)
    if not any(week.values()):
        return "The timetable is empty."
    out = []
    todays = timetable.get_todays_classes(now=now, db_path=db_path)
    out.append("Today's classes: " + ("; ".join(_slot_line(s) for s in todays)
                                      if todays else "none"))
    nxt = timetable.get_next_class(now=now, db_path=db_path)
    if nxt:
        when = ("today" if nxt["days_until"] == 0 else
                "tomorrow" if nxt["days_until"] == 1 else
                f"on {nxt['day_of_week']}" if nxt["days_until"] < 7 else
                f"next {nxt['day_of_week']}")
        out.append(f"Next class: {_slot_line(nxt)} {when} at {nxt['start_time']}")
    out.append("Weekly timetable:")
    for day, slots in week.items():
        out.append(f"  {day}: " + ("; ".join(_slot_line(s) for s in slots)
                                   if slots else "no classes"))
    return "\n".join(out)


def _section_assignments(now, db_path):
    today = now.date()
    pending = assignments.get_pending_assignments(today=today, db_path=db_path)
    done = assignments.list_assignments(status="Completed", today=today, db_path=db_path)
    if not pending and not done:
        return "No assignments have been added yet."
    out = [f"Pending: {len(pending)}   Completed: {len(done)}"]
    for a in pending[:MAX_PENDING_SHOWN]:
        out.append(f"- {a['course_code']} \"{a['title']}\" - due {a['due_date']} "
                   f"({_days_phrase(a['days_left'])}) - state: {a['state']} - "
                   f"priority: {a['priority']}")
    if len(pending) > MAX_PENDING_SHOWN:
        out.append(f"(+{len(pending) - MAX_PENDING_SHOWN} more pending not shown)")
    return "\n".join(out)


def _attendance_line(s):
    label = s.get("course_code", "Overall")
    if s["percentage"] is None:
        return f"{label}: no sessions recorded yet"
    status = (f"BELOW the {s['threshold']:g}% warning threshold" if s["below_threshold"]
              else f"meets the {s['threshold']:g}% warning threshold")
    return (f"{label}: {s['percentage']}% ({s['present']} present, {s['late']} late, "
            f"{s['excused']} excused, {s['absent']} absent; {s['total']} sessions) - {status}")


def _section_attendance(now, db_path):
    summaries = attendance.get_all_summaries(db_path)
    if not summaries:
        return "No courses have been added yet."
    out = ["Attendance % = (present + late + excused) / all recorded sessions."]
    out += [_attendance_line(s) for s in summaries]
    out.append(_attendance_line(attendance.get_overall_attendance(db_path)))
    return "\n".join(out)


def _section_notes(now, db_path):
    recent = notes.get_recent_notes(limit=MAX_NOTE_TITLES, db_path=db_path)
    if not recent:
        return "No notes have been saved yet."
    out = ["(Titles only - the text of the notes is not included here.)"]
    for n in recent:
        tags = f" [tags: {', '.join(n['tags'])}]" if n["tags"] else ""
        out.append(f"- {n['course_code']}: {n['title']}{tags} "
                   f"(updated {(n['updated_at'] or '')[:10]})")
    return "\n".join(out)


_SECTIONS = {
    "courses": ("COURSES", _section_courses), "timetable": ("TIMETABLE", _section_timetable),
    "assignments": ("ASSIGNMENTS", _section_assignments), "attendance": ("ATTENDANCE", _section_attendance),
    "notes": ("NOTES", _section_notes),
}


def build_overview_context(topics=None, now=None, db_path=None):
    now = now or datetime.now()
    wanted = [t for t in TOPICS if t in set(topics or TOPICS)]
    unknown = set(topics or ()) - set(TOPICS)
    if unknown:
        raise ValueError(f"Unknown topic(s): {', '.join(sorted(unknown))}")
    blocks = [_header(now, db_path)]
    for topic in wanted:
        title, builder = _SECTIONS[topic]
        blocks.append(f"== {title} ==\n{builder(now, db_path)}")
    return {"text": "\n\n".join(blocks), "sections": wanted}
