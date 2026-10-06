import os
import sqlite3
import tempfile
import unittest
from datetime import date

from student_os import assignments, attendance, courses, db, notes, settings
from student_os.dates import parse_date

TODAY = date(2026, 10, 5)


class A3Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.db")
        db.init_db(self.path)
        self.cid = courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def second_course(self):
        return courses.add_course("MTH201", "Linear Algebra", 3, db_path=self.path)


class TestDates(unittest.TestCase):
    def test_accepts_and_rejects(self):
        self.assertEqual(parse_date("2026-10-05"), date(2026, 10, 5))
        for bad in ["20261005", "05/10/2026", "2026-13-01", "2026-02-30", "", None, "abc"]:
            with self.assertRaises(ValueError, msg=bad):
                parse_date(bad)


class TestAssignments(A3Base):
    def add(self, title="HW", due="2026-10-08", **kw):
        return assignments.add_assignment(self.cid, title, due, db_path=self.path, **kw)

    def test_state_calculation(self):
        cases = {"2026-10-04": "Overdue", "2026-10-05": "Due Today", "2026-10-06": "Due Soon",
                 "2026-10-08": "Due Soon", "2026-10-09": "Upcoming"}
        for due, expected in cases.items():
            self.assertEqual(assignments.get_assignment_state(due, "Pending", TODAY), expected, due)
        self.assertEqual(assignments.get_assignment_state("2026-01-01", "Completed", TODAY),
                         "Completed")

    def test_state_is_never_stored(self):
        a = self.add(due="2026-10-04")
        later = date(2026, 12, 1)
        self.assertEqual(assignments.get_assignment(a, TODAY, self.path)["state"], "Overdue")
        a2 = self.add(due="2026-11-30")
        self.assertEqual(assignments.get_assignment(a2, TODAY, self.path)["state"], "Upcoming")
        self.assertEqual(assignments.get_assignment(a2, later, self.path)["state"], "Overdue")

    def test_validation(self):
        bad = [dict(title="", due_date="2026-10-08"), dict(title="x", due_date="08-10-2026"),
               dict(title="x", due_date="2026-10-08", priority="Urgent"),
               dict(title="x", due_date="2026-10-08", status="Done")]
        for kw in bad:
            with self.assertRaises(ValueError, msg=kw):
                assignments.add_assignment(self.cid, db_path=self.path, **kw)
        with self.assertRaises(LookupError):
            assignments.add_assignment(999, "x", "2026-10-08", db_path=self.path)

    def test_mark_complete_and_update(self):
        a = self.add(due="2026-10-04")
        done = assignments.mark_complete(a, TODAY, self.path)
        self.assertEqual((done["status"], done["state"]), ("Completed", "Completed"))
        up = assignments.update_assignment(a, title="HW 2", priority="high",
                                           status="pending", today=TODAY, db_path=self.path)
        self.assertEqual((up["title"], up["priority"], up["state"]), ("HW 2", "High", "Overdue"))

    def test_update_errors(self):
        a = self.add()
        with self.assertRaises(ValueError):
            assignments.update_assignment(a, id=5, db_path=self.path)
        with self.assertRaises(LookupError):
            assignments.update_assignment(999, title="x", db_path=self.path)
        with self.assertRaises(LookupError):
            assignments.update_assignment(a, course_id=999, db_path=self.path)

    def test_delete(self):
        a = self.add()
        assignments.delete_assignment(a, self.path)
        self.assertIsNone(assignments.get_assignment(a, db_path=self.path))
        with self.assertRaises(LookupError):
            assignments.delete_assignment(a, self.path)

    def test_listing_filters_and_sorting(self):
        other = self.second_course()
        self.add("late", "2026-10-01")
        self.add("low-soon", "2026-10-07", priority="Low")
        self.add("high-soon", "2026-10-07", priority="High")
        done = self.add("finished", "2026-10-02")
        assignments.mark_complete(done, TODAY, self.path)
        assignments.add_assignment(other, "other-course", "2026-12-01", db_path=self.path)
        titles = [a["title"] for a in assignments.list_assignments(today=TODAY, db_path=self.path)]
        self.assertEqual(titles, ["late", "finished", "high-soon", "low-soon", "other-course"])
        self.assertEqual(len(assignments.list_assignments(course_id=other, db_path=self.path)), 1)
        self.assertEqual([a["title"] for a in assignments.get_overdue_assignments(TODAY, self.path)],
                         ["late"])
        self.assertEqual(len(assignments.get_pending_assignments(TODAY, self.path)), 4)
        self.assertEqual(len(assignments.list_assignments(priority="high", db_path=self.path)), 1)
        self.assertEqual(len(assignments.list_assignments(state="due soon", today=TODAY,
                                                          db_path=self.path)), 2)


class TestAttendance(A3Base):
    def rec(self, day, status, cid=None):
        return attendance.record_attendance(cid or self.cid, day, status,
                                            today=TODAY, db_path=self.path)

    def test_percentage_formula_excused_counts_as_attended_and_in_total(self):
        self.assertEqual(attendance.calculate_percentage({}), None)
        self.assertEqual(attendance.calculate_percentage({"Excused": 1}), 100)
        counts = {"Present": 3, "Late": 1, "Excused": 1, "Absent": 5}
        self.assertEqual(attendance.calculate_percentage(counts), 50.0)
        self.assertEqual(attendance.calculate_percentage({"Absent": 2, "Excused": 2}), 50.0)

    def test_course_summary(self):
        for i, s in enumerate(["Present", "Present", "Late", "Excused", "Absent"], start=1):
            self.rec(f"2026-10-0{i}", s)
        s = attendance.get_course_summary(self.cid, self.path)
        self.assertEqual((s["total"], s["present"], s["late"], s["excused"], s["absent"]),
                         (5, 2, 1, 1, 1))
        self.assertEqual(s["percentage"], 80.0)
        self.assertFalse(s["below_threshold"])

    def test_threshold_boundary_and_warning(self):
        for i, s in enumerate(["Present", "Present", "Present", "Absent"], start=1):
            self.rec(f"2026-10-0{i}", s)
        self.assertFalse(attendance.get_course_summary(self.cid, self.path)["below_threshold"])
        self.assertEqual(attendance.get_courses_below_threshold(self.path), [])
        settings.set_attendance_threshold(80, self.path)
        s = attendance.get_course_summary(self.cid, self.path)
        self.assertTrue(s["below_threshold"])
        self.assertEqual(len(attendance.get_courses_below_threshold(self.path)), 1)

    def test_no_records_means_no_percentage_and_no_warning(self):
        s = attendance.get_course_summary(self.cid, self.path)
        self.assertEqual((s["total"], s["percentage"], s["below_threshold"]), (0, None, False))

    def test_recording_same_day_overwrites(self):
        self.rec("2026-10-01", "Present")
        self.rec("2026-10-01", "absent")
        records = attendance.get_attendance_records(self.cid, self.path)
        self.assertEqual([(r["date"], r["status"]) for r in records], [("2026-10-01", "Absent")])

    def test_validation(self):
        with self.assertRaises(ValueError):
            self.rec("2026-10-01", "Maybe")
        with self.assertRaises(ValueError):
            self.rec("not-a-date", "Present")
        with self.assertRaisesRegex(ValueError, "future"):
            self.rec("2026-10-06", "Present")
        self.rec("2026-10-05", "Present")
        with self.assertRaises(LookupError):
            self.rec("2026-10-01", "Present", cid=999)

    def test_delete_record(self):
        self.rec("2026-10-01", "Present")
        attendance.delete_attendance(self.cid, "2026-10-01", self.path)
        with self.assertRaises(LookupError):
            attendance.delete_attendance(self.cid, "2026-10-01", self.path)

    def test_overall_and_all_summaries(self):
        other = self.second_course()
        self.rec("2026-10-01", "Present")
        self.rec("2026-10-02", "Absent")
        self.rec("2026-10-01", "Present", cid=other)
        self.rec("2026-10-02", "Present", cid=other)
        overall = attendance.get_overall_attendance(self.path)
        self.assertEqual((overall["total"], overall["percentage"]), (4, 75.0))
        by_code = {s["course_code"]: s for s in attendance.get_all_summaries(self.path)}
        self.assertEqual((by_code["CSC301"]["percentage"], by_code["MTH201"]["percentage"]),
                         (50.0, 100.0))

    def test_overall_with_no_records(self):
        overall = attendance.get_overall_attendance(self.path)
        self.assertEqual((overall["total"], overall["percentage"], overall["below_threshold"]),
                         (0, None, False))

    def test_unrounded_value_used_for_warning(self):
        for i, s in enumerate(["Present", "Present", "Absent"], start=1):
            self.rec(f"2026-10-0{i}", s)
        settings.set_attendance_threshold(66.7, self.path)
        self.assertTrue(attendance.get_course_summary(self.cid, self.path)["below_threshold"])


class TestNotes(A3Base):
    def test_tag_normalisation(self):
        self.assertEqual(notes.normalize_tags("Exam, exam , Week 1,"), ["exam", "week 1"])
        self.assertEqual(notes.normalize_tags(["A", "a", " b "]), ["a", "b"])
        self.assertEqual(notes.normalize_tags(None), [])

    def test_add_get_update_delete(self):
        n = notes.add_note(self.cid, " Sorting ", "quick sort notes", "Exam, Week 1", self.path)
        got = notes.get_note(n, self.path)
        self.assertEqual((got["title"], got["tags"], got["course_code"]),
                         ("Sorting", ["exam", "week 1"], "CSC301"))
        up = notes.update_note(n, content="merge sort too", tags="revision", db_path=self.path)
        self.assertEqual((up["content"], up["tags"]), ("merge sort too", ["revision"]))
        notes.delete_note(n, self.path)
        self.assertIsNone(notes.get_note(n, self.path))
        with self.assertRaises(LookupError):
            notes.delete_note(n, self.path)

    def test_validation(self):
        with self.assertRaises(ValueError):
            notes.add_note(self.cid, "  ", db_path=self.path)
        with self.assertRaises(LookupError):
            notes.add_note(999, "x", db_path=self.path)
        n = notes.add_note(self.cid, "x", db_path=self.path)
        with self.assertRaises(ValueError):
            notes.update_note(n, title="", db_path=self.path)
        with self.assertRaises(ValueError):
            notes.update_note(n, created_at="2020", db_path=self.path)
        with self.assertRaises(LookupError):
            notes.update_note(999, title="x", db_path=self.path)

    def test_filter_by_course_tag_and_search(self):
        other = self.second_course()
        notes.add_note(self.cid, "Sorting", "quick sort", "exam", self.path)
        notes.add_note(self.cid, "Graphs", "BFS and DFS", "revision,week 2", self.path)
        notes.add_note(other, "Matrices", "determinants", "exam", self.path)
        ids = lambda **kw: sorted(n["title"] for n in notes.list_notes(db_path=self.path, **kw))
        self.assertEqual(ids(), ["Graphs", "Matrices", "Sorting"])
        self.assertEqual(ids(course_id=self.cid), ["Graphs", "Sorting"])
        self.assertEqual(ids(tag="exam"), ["Matrices", "Sorting"])
        self.assertEqual(ids(tag="ex"), [])
        self.assertEqual(ids(tag="Week 2"), ["Graphs"])
        self.assertEqual(ids(search="bfs"), ["Graphs"])
        self.assertEqual(ids(search="MATRI"), ["Matrices"])
        self.assertEqual(ids(search="exam", course_id=other), ["Matrices"])

    def test_wildcards_are_literal(self):
        notes.add_note(self.cid, "Score", "got 100% today", "", self.path)
        notes.add_note(self.cid, "Other", "nothing here", "", self.path)
        found = notes.list_notes(search="100%", db_path=self.path)
        self.assertEqual([n["title"] for n in found], ["Score"])
        self.assertEqual(notes.list_notes(search="%", db_path=self.path)[0]["title"], "Score")
        self.assertEqual(len(notes.list_notes(search="%", db_path=self.path)), 1)
        self.assertEqual(notes.list_notes(search="_", db_path=self.path), [])

    def test_recent_and_tags(self):
        for i in range(7):
            notes.add_note(self.cid, f"n{i}", "", "b,a" if i == 0 else "", self.path)
        recent = notes.get_recent_notes(3, self.path)
        self.assertEqual([n["title"] for n in recent], ["n6", "n5", "n4"])
        self.assertEqual(notes.list_all_tags(db_path=self.path), ["a", "b"])
        self.assertEqual(notes.list_all_tags(course_id=self.second_course(), db_path=self.path), [])


class TestSettings(A3Base):
    def test_threshold(self):
        self.assertEqual(settings.get_attendance_threshold(self.path), 75.0)
        self.assertEqual(settings.set_attendance_threshold("80", self.path), 80.0)
        self.assertEqual(settings.get_attendance_threshold(self.path), 80.0)
        for bad in (101, -1, "abc", None):
            with self.assertRaises(ValueError, msg=bad):
                settings.set_attendance_threshold(bad, self.path)
        settings.set_attendance_threshold(0, self.path)
        settings.set_attendance_threshold(100, self.path)

    def test_corrupt_threshold_falls_back_to_default(self):
        settings.set_setting("attendance_threshold", "garbage", self.path)
        self.assertEqual(settings.get_attendance_threshold(self.path), 75.0)

    def test_generic_settings(self):
        self.assertEqual(settings.get_setting("theme", "dark", self.path), "dark")
        settings.set_setting("theme", "light", self.path)
        settings.set_setting("theme", "blue", self.path)
        self.assertEqual(settings.get_setting("theme", db_path=self.path), "blue")
        with self.assertRaises(ValueError):
            settings.set_setting(" ", "x", self.path)

    def test_backup(self):
        dest = os.path.join(self.tmp.name, "bk")
        first = settings.backup_database(dest, self.path)
        second = settings.backup_database(dest, self.path)
        self.assertNotEqual(first, second)
        self.assertEqual(len(os.listdir(dest)), 2)
        conn = sqlite3.connect(first)
        self.assertEqual(conn.execute("SELECT code FROM courses").fetchone()[0], "CSC301")
        conn.close()

    def test_default_backup_folder_is_next_to_db(self):
        out = settings.backup_database(db_path=self.path)
        self.assertEqual(os.path.dirname(out), os.path.join(self.tmp.name, "backups"))


if __name__ == "__main__":
    unittest.main()
