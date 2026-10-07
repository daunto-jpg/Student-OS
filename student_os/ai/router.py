"""Question routing for the AI Assistant (Partition C, Member C2).

Decides two things from the student's question:
  1. Is it about the student's own data (overview) or a general academic question?
  2. If overview: which topics' data should be collected and sent?

Plain keyword rules, no AI call - so it is instant, free, works offline and
is fully testable. Keywords come in two strengths:
  STRONG  words that almost always mean the student's own data
          ("assignment", "attendance", "timetable", "deadline", "overdue" ...)
  WEAK    words that are also ordinary English / Computer Science
          ("class", "course", "late", "present", "note" ...). They only count
          when the question also sounds personal ("my", "do I", "am I" ...),
          so "What is a class in Python?" stays a general question. The personal cue
          is an ownership phrase ("my", "do I have", "have I", "am I"); a bare "I" is not
          enough, so "How do I write good lecture notes?" is still a general question.
"""
import re
from dataclasses import dataclass

from student_os.ai.context_builder import TOPICS

AUTO, GENERAL, OVERVIEW = "auto", "general", "overview"
MODES = (AUTO, GENERAL, OVERVIEW)

_STRONG = {
    "timetable": r"timetables?|schedules?|next class|classes today|lectures? today",
    "assignments": r"assignments?|homework|deadlines?|due|overdue|submit|submission|"
                   r"submissions|coursework|pending",
    "attendance": r"attendance|absent|absences|excused|attended|attendance rate|"
                  r"missed classes|missed lectures",
    "courses": r"credit units?|credit hours?|lecturers?|my courses|registered courses",
    "notes": r"my notes|saved notes",
}
_WEAK = {
    "timetable": r"class|classes|lectures?|venue|today|tomorrow|"
                 r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
                 r"what time|when is|when are",
    "assignments": r"project|projects|work|tasks?",
    "attendance": r"late|present|missed|miss|skipped|percentage",
    "courses": r"courses?|units?|subjects?|code",
    "notes": r"notes?|lecture notes|tags?",
}
_DAY_CUES = r"what do i have|my day|this week|today|tomorrow|what's on|whats on"
_PERSONAL = (r"\b(my|mine|our|am i|have i|did i|do i have|i have|i've|ive|i'm|im|"
             r"i missed|i attended)\b")


def _find(patterns, text):
    return {topic for topic, pat in patterns.items()
            if re.search(rf"\b(?:{pat})\b", text)}


@dataclass(frozen=True)
class Route:
    kind: str
    topics: tuple = ()
    reason: str = ""


def route_question(question, mode=AUTO):
    """Return a Route for the question."""
    text = (question or "").strip().lower()
    if not text:
        raise ValueError("Type a question first.")
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode!r}")
    if mode == GENERAL:
        return Route("general", (), "general mode chosen")

    personal = bool(re.search(_PERSONAL, text))
    strong = _find(_STRONG, text)
    weak = _find(_WEAK, text)
    day_cue = bool(re.search(rf"\b(?:{_DAY_CUES})\b", text))

    if mode == OVERVIEW:
        found = strong | weak
        if day_cue:
            found |= {"timetable", "assignments"}
        topics = tuple(t for t in TOPICS if t in found) or TOPICS
        return Route("overview", topics,
                     "matched topics" if found else "no specific topic: using all data")

    found = set(strong)
    if personal:
        found |= weak
        if day_cue:
            found |= {"timetable", "assignments"}
    if found:
        return Route("overview", tuple(t for t in TOPICS if t in found),
                     "question refers to the student's own data")
    return Route("general", (), "no personal-data keywords")
