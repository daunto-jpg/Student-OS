"""Tests for Partition C, Member C2: context builder, router, assistant.

Uses a real temporary SQLite database filled through the Partition A modules,
a fixed 'now', and a fake Gemini transport (no key / internet needed).
"""
import os
import tempfile
import unittest
from datetime import datetime

from student_os import (
    assignments, attendance, courses, db, notes, profile, settings, timetable,
)
from student_os.ai import context_builder as cb
from student_os.ai import prompts, router
from student_os.ai.assistant import Assistant
from student_os.ai.errors import AIUnavailableError
from student_os.ai.gemini_client import GeminiClient

NOW = datetime(2026, 10, 5, 14, 0)          # a Monday afternoon
KEY = "AIzaFAKE-KEY-1234567890"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.db")
        db.init_db(self.path)
        p = self.path
        profile.save_profile("Fortune Deji-Aderinto", "2026/2027", "First Semester", db_path=p)
        self.csc = courses.add_course("CSC301", "Algorithms", 3, "Dr Ade", "LT1", db_path=p)
        self.mth = courses.add_course("MTH201", "Linear Algebra", 2, db_path=p)
        timetable.add_slot(self.csc, "Monday", "08:00", "10:00", db_path=p)
        timetable.add_slot(self.mth, "Monday", "16:00", "18:00", "Hall B", db_path=p)
        timetable.add_slot(self.csc, "Wednesday", "10:00", "12:00", db_path=p)
        self.overdue = assignments.add_assignment(self.csc, "Sorting report", "2026-10-03",
                                                  "High", db_path=p)
        assignments.add_assignment(self.csc, "Graph quiz", "2026-10-06", db_path=p)
        assignments.add_assignment(self.mth, "Matrix set", "2026-10-20", "Low", db_path=p)
        done = assignments.add_assignment(self.mth, "Old set", "2026-09-01", db_path=p)
        assignments.mark_complete(done, today=NOW.date(), db_path=p)
        # CSC301: 3 present + 1 excused + 1 absent = 80%. MTH201: 1 present + 3 absent = 25%.
        for d, s in [("2026-09-14", "Present"), ("2026-09-21", "Present"),
                     ("2026-09-28", "Present"), ("2026-09-07", "Excused"),
                     ("2026-09-30", "Absent")]:
            attendance.record_attendance(self.csc, d, s, today=NOW.date(), db_path=p)
        for d, s in [("2026-09-15", "Present"), ("2026-09-22", "Absent"),
                     ("2026-09-29", "Absent"), ("2026-10-01", "Absent")]:
            attendance.record_attendance(self.mth, d, s, today=NOW.date(), db_path=p)
        self.note = notes.add_note(self.csc, "Binary search", "Halve the range each step.",
                                   "exam, week 3", db_path=p)
        notes.add_note(self.mth, "Determinants", "SECRET-NOTE-BODY", "", db_path=p)

    def tearDown(self):
        self.tmp.cleanup()

    def overview(self, topics=None):
        return cb.build_overview_context(topics, now=NOW, db_path=self.path)


class TestNoteContext(Base):
    def test_fields(self):
        c = cb.build_note_context(self.note, self.path)
        self.assertEqual((c["course_code"], c["title"], c["tags"]),
                         ("CSC301", "Binary search", ["exam", "week 3"]))
        self.assertEqual(c["content"], "Halve the range each step.")
        self.assertFalse(c["truncated"])

    def test_long_note_is_cut_and_flagged(self):
        nid = notes.add_note(self.csc, "Long", "x" * (cb.MAX_NOTE_CHARS + 500), db_path=self.path)
        c = cb.build_note_context(nid, self.path)
        self.assertEqual(len(c["content"]), cb.MAX_NOTE_CHARS)
        self.assertTrue(c["truncated"])
        self.assertEqual(c["original_length"], cb.MAX_NOTE_CHARS + 500)

    def test_missing_note(self):
        with self.assertRaises(LookupError):
            cb.build_note_context(9999, self.path)

    def test_feeds_prompt_builder(self):
        p = prompts.build_prompt(prompts.SUMMARIZE_NOTE,
                                 note=cb.build_note_context(self.note, self.path))
        self.assertIn("Halve the range", p)


class TestOverviewContext(Base):
    def test_only_requested_sections(self):
        r = self.overview(["attendance"])
        self.assertEqual(r["sections"], ["attendance"])
        self.assertIn("== ATTENDANCE ==", r["text"])
        for other in ("TIMETABLE", "ASSIGNMENTS", "COURSES", "NOTES"):
            self.assertNotIn(f"== {other} ==", r["text"])

    def test_default_is_everything_in_fixed_order(self):
        self.assertEqual(self.overview()["sections"], list(cb.TOPICS))

    def test_unknown_topic(self):
        with self.assertRaises(ValueError):
            self.overview(["gossip"])

    def test_header_has_real_date_and_first_name_only(self):
        text = self.overview(["courses"])["text"]
        self.assertIn("Monday, 05 October 2026, 14:00", text)
        self.assertIn("Student: Fortune", text)
        self.assertNotIn("Deji-Aderinto", text)
        self.assertIn("2026/2027, First Semester", text)

    def test_assignment_states_come_from_python(self):
        text = self.overview(["assignments"])["text"]
        self.assertIn("Pending: 3   Completed: 1", text)
        self.assertIn('"Sorting report" - due 2026-10-03 (overdue by 2 days) - state: Overdue',
                      text)
        self.assertIn('"Graph quiz" - due 2026-10-06 (due tomorrow) - state: Due Soon', text)
        self.assertIn("state: Upcoming", text)
        self.assertNotIn("Old set", text)            # completed items are only counted

    def test_attendance_numbers_match_partition_a(self):
        text = self.overview(["attendance"])["text"]
        self.assertIn("CSC301: 80.0% (3 present, 0 late, 1 excused, 1 absent; 5 sessions)", text)
        self.assertIn("meets the 75% warning threshold", text)
        self.assertIn("MTH201: 25.0%", text)
        self.assertIn("BELOW the 75% warning threshold", text)
        overall = attendance.get_overall_attendance(self.path)
        self.assertIn(f"Overall: {overall['percentage']}%", text)

    def test_attendance_follows_changed_threshold(self):
        settings.set_attendance_threshold(90, self.path)
        text = self.overview(["attendance"])["text"]
        self.assertIn("CSC301: 80.0%", text)
        self.assertIn("BELOW the 90% warning threshold", text.split("CSC301")[1].split("\n")[0])

    def test_course_with_no_records(self):
        courses.add_course("PHY101", "Physics", 2, db_path=self.path)
        self.assertIn("PHY101: no sessions recorded yet", self.overview(["attendance"])["text"])

    def test_timetable_today_and_next(self):
        text = self.overview(["timetable"])["text"]
        self.assertIn("Today's classes: 08:00-10:00 CSC301 Algorithms (LT1); "
                      "16:00-18:00 MTH201 Linear Algebra (Hall B)", text)
        self.assertIn("Next class: 16:00-18:00 MTH201 Linear Algebra (Hall B) today at 16:00",
                      text)
        self.assertIn("Tuesday: no classes", text)

    def test_next_class_rolls_to_another_day(self):
        late = cb.build_overview_context(["timetable"], now=datetime(2026, 10, 5, 19, 0),
                                         db_path=self.path)
        self.assertIn("on Wednesday at 10:00", late["text"])

    def test_notes_are_titles_only(self):
        text = self.overview(["notes"])["text"]
        self.assertIn("Binary search [tags: exam, week 3]", text)
        self.assertIn("Determinants", text)
        self.assertNotIn("SECRET-NOTE-BODY", text)
        self.assertNotIn("Halve the range", text)

    def test_courses_section(self):
        text = self.overview(["courses"])["text"]
        self.assertIn("CSC301 - Algorithms | 3 credit unit(s) | lecturer: Dr Ade | venue: LT1",
                      text)

    def test_empty_database_gives_friendly_text(self):
        empty = os.path.join(self.tmp.name, "empty.db")
        db.init_db(empty)
        r = cb.build_overview_context(None, now=NOW, db_path=empty)
        for phrase in ("No courses have been added yet.", "The timetable is empty.",
                       "No assignments have been added yet.", "No notes have been saved yet."):
            self.assertIn(phrase, r["text"])
        self.assertNotIn("Student:", r["text"])

    def test_pending_list_is_capped(self):
        for i in range(cb.MAX_PENDING_SHOWN + 3):
            assignments.add_assignment(self.csc, f"Bulk {i}", "2026-12-01", db_path=self.path)
        text = self.overview(["assignments"])["text"]
        self.assertIn("more pending not shown", text)


class TestRouter(unittest.TestCase):
    def kind(self, q, mode="auto"):
        return router.route_question(q, mode)

    def test_general_questions_stay_general(self):
        for q in ("What is a class in Python?", "Explain binary search trees",
                  "What does late binding mean?", "Define a present value",
                  "How do I write good lecture notes?", "Explain recursion"):
            self.assertEqual(self.kind(q).kind, "general", q)

    def test_personal_data_questions(self):
        cases = {
            "When is my next class?": ("timetable",),
            "What assignments are due?": ("assignments",),
            "Which of my assignments are overdue?": ("assignments",),
            "Am I below the attendance threshold?": ("attendance",),
            "What is my attendance in CSC301?": ("attendance",),
            "Who is my lecturer for MTH201?": ("courses",),
            "What do I have today?": ("timetable", "assignments"),
            "Do I have any classes on Friday?": ("timetable",),
            "Have I missed any lectures?": ("timetable", "attendance"),
            "Which of my notes mention sorting?": ("notes",),
        }
        for q, topics in cases.items():
            r = self.kind(q)
            self.assertEqual(r.kind, "overview", q)
            for t in topics:
                self.assertIn(t, r.topics, q)

    def test_topics_keep_canonical_order(self):
        r = self.kind("Show my attendance and assignments")
        self.assertEqual(r.topics, ("assignments", "attendance"))

    def test_forced_general_never_collects_data(self):
        r = self.kind("What are my assignments?", "general")
        self.assertEqual((r.kind, r.topics), ("general", ()))

    def test_forced_overview_without_keywords_uses_everything(self):
        r = self.kind("How am I doing this semester?", "overview")
        self.assertEqual((r.kind, r.topics), ("overview", router.TOPICS))

    def test_forced_overview_with_weak_keyword(self):
        self.assertEqual(self.kind("Tell me about my courses", "overview").topics, ("courses",))

    def test_validation(self):
        for bad in ("", "   ", None):
            with self.assertRaises(ValueError):
                router.route_question(bad)
        with self.assertRaises(ValueError):
            router.route_question("hi", "chaos")


class FakeTransport:
    def __init__(self, reply="FAKE ANSWER", raises=None):
        self.reply, self.raises, self.calls = reply, raises, []

    def __call__(self, **kw):
        self.calls.append(kw)
        if self.raises:
            raise self.raises
        return self.reply


class TestAssistant(Base):
    def make(self, **kw):
        t = FakeTransport(**kw)
        a = Assistant(GeminiClient(api_key=KEY, transport=t), self.path, clock=lambda: NOW)
        return a, t

    def test_general_question_sends_no_student_data(self):
        a, t = self.make()
        r = a.ask("What is a hash table?")
        self.assertTrue(r.ok)
        self.assertEqual((r.text, r.feature, r.sections), ("FAKE ANSWER", "general_qa", []))
        prompt = t.calls[0]["prompt"]
        for private in ("CSC301", "Fortune", "Sorting report", "SECRET-NOTE-BODY"):
            self.assertNotIn(private, prompt)

    def test_overview_question_sends_only_relevant_data(self):
        a, t = self.make()
        r = a.ask("What assignments are due?")
        self.assertEqual((r.feature, r.sections), ("academic_overview", ["assignments"]))
        prompt = t.calls[0]["prompt"]
        self.assertIn("Sorting report", prompt)
        self.assertIn("Monday, 05 October 2026", prompt)
        self.assertNotIn("== ATTENDANCE ==", prompt)
        self.assertNotIn("SECRET-NOTE-BODY", prompt)

    def test_offline_overview_falls_back_to_python_facts(self):
        a, _ = self.make(raises=ConnectionError("down"))
        r = a.ask("What assignments are due?")
        self.assertFalse(r.ok)
        self.assertEqual(r.reason, "offline")
        self.assertTrue(r.fallback)
        self.assertIn("Can't reach Gemini", r.text)
        self.assertIn("overdue by 2 days", r.text)       # real answer, no AI needed

    def test_offline_general_question_just_explains(self):
        a, _ = self.make(raises=TimeoutError())
        r = a.ask("What is a hash table?")
        self.assertEqual((r.ok, r.reason, r.fallback), (False, "offline", False))
        self.assertIn("Everything except the AI Assistant still works offline", r.text)

    def test_no_key(self):
        a = Assistant(GeminiClient(environ={}, transport=FakeTransport()), self.path,
                      clock=lambda: NOW)
        self.assertFalse(a.available)
        r = a.ask("What is a hash table?")
        self.assertEqual((r.ok, r.reason), (False, "no_key"))
        self.assertIn("GEMINI_API_KEY", r.text)

    def test_note_features(self):
        for method, feature, needle in [
            ("summarize_note", "summarize_note", "Summarize the lecture note"),
            ("explain_note", "explain_note", "Explain the lecture note"),
            ("revision_questions", "revision_questions", "Write 5 revision questions"),
        ]:
            a, t = self.make()
            r = getattr(a, method)(self.note)
            self.assertEqual((r.ok, r.feature, r.text), (True, feature, "FAKE ANSWER"))
            self.assertIn(needle, t.calls[0]["prompt"])
            self.assertIn("Halve the range", t.calls[0]["prompt"])

    def test_revision_count_and_focus_pass_through(self):
        a, t = self.make()
        a.revision_questions(self.note, count=8)
        self.assertIn("Write 8 revision questions", t.calls[0]["prompt"])
        a.explain_note(self.note, focus="halving")
        self.assertIn("halving", t.calls[1]["prompt"])

    def test_note_problems_come_back_as_results_not_exceptions(self):
        a, t = self.make()
        r = a.summarize_note(9999)
        self.assertEqual((r.ok, r.reason), (False, "not_found"))
        empty = notes.add_note(self.csc, "Blank", "   ", db_path=self.path)
        r = a.summarize_note(empty)
        self.assertEqual((r.ok, r.reason), (False, "invalid_input"))
        r = a.revision_questions(self.note, count=99)
        self.assertEqual((r.ok, r.reason), (False, "invalid_input"))
        self.assertEqual(t.calls, [])                    # nothing was sent for bad input

    def test_bad_questions(self):
        a, t = self.make()
        for q in ("", "   "):
            self.assertEqual(a.ask(q).reason, "invalid_input")
        self.assertEqual(a.ask("x " * 2000).reason, "invalid_input")
        self.assertEqual(t.calls, [])

    def test_long_note_notice(self):
        nid = notes.add_note(self.csc, "Long", "x" * (cb.MAX_NOTE_CHARS + 1), db_path=self.path)
        a, _ = self.make()
        self.assertIn("only the first", a.summarize_note(nid).notice)
        self.assertEqual(a.summarize_note(self.note).notice, "")

    def test_gemini_failure_on_note_feature_keeps_notice_and_reason(self):
        a, _ = self.make(raises=AIUnavailableError("nope"))
        r = a.summarize_note(self.note)
        self.assertEqual((r.ok, r.reason), (False, "offline"))


if __name__ == "__main__":
    unittest.main()
