"""B2: the pure-logic helpers behind Courses, Timetable and Settings, tested against
the REAL Partition A modules and a real temporary database (no GUI needed)."""
import os
import tempfile
import unittest
from datetime import datetime

from student_os import courses, db, profile, settings, timetable
from student_os.ui import courses_data as cd
from student_os.ui import settings_data as sd
from student_os.ui import timetable_data as td

NOW = datetime(2026, 10, 7, 10, 30)    # a Wednesday


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "b2.db")
        db.init_db(self.path)

    def tearDown(self):
        self.tmp.cleanup()


class CoursesDataTests(Base):
    def test_credit_text_singular_and_plural(self):
        self.assertEqual(cd.credit_text(1), "1 credit unit")
        self.assertEqual(cd.credit_text(3), "3 credit units")

    def test_summary_skips_blank_parts(self):
        full = {"lecturer": "Dr Musa", "venue": "LT1", "credit_unit": 3}
        self.assertEqual(cd.course_summary(full), "Dr Musa  |  LT1  |  3 credit units")
        bare = {"lecturer": "", "venue": "", "credit_unit": 2}
        self.assertEqual(cd.course_summary(bare), "2 credit units")

    def test_search_goes_through_partition_a(self):
        courses.add_course("CSC301", "Algorithms", 3, lecturer="Dr Musa", db_path=self.path)
        courses.add_course("MTH201", "Linear Algebra", 2, db_path=self.path)
        self.assertEqual(len(cd.load_courses("", self.path)), 2)
        self.assertEqual([c["code"] for c in cd.load_courses("musa", self.path)], ["CSC301"])
        self.assertEqual(len(cd.load_courses("algebra", self.path)), 1)

    def test_count_and_empty_text(self):
        self.assertEqual(cd.count_text(1), "1 course")
        self.assertEqual(cd.count_text(4), "4 courses")
        self.assertEqual(cd.count_text(1, "x"), "1 match")
        self.assertEqual(cd.count_text(0, "x"), "0 matches")
        self.assertIn("No courses match", cd.empty_text("zzz"))
        self.assertIn("Add course", cd.empty_text())

    def test_delete_warning_lists_real_linked_records(self):
        from student_os import assignments, attendance, notes
        cid = courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        p = self.path
        timetable.add_slot(cid, "Monday", "08:00", "10:00", db_path=p)
        assignments.add_assignment(cid, "A1", "2026-10-20", db_path=p)
        assignments.add_assignment(cid, "A2", "2026-10-21", db_path=p)
        attendance.record_attendance(cid, "2026-10-01", "Present", today=NOW.date(), db_path=p)
        notes.add_note(cid, "N", "x", db_path=p)
        counts = courses.count_linked_records(cid, db_path=p)
        msg = cd.delete_warning(courses.get_course(cid, p), counts)
        for expected in ("CSC301 - Algorithms", "1 class slot", "2 assignments",
                         "1 attendance record", "1 note", "cannot be undone"):
            self.assertIn(expected, msg)

    def test_delete_warning_when_nothing_linked(self):
        cid = courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        msg = cd.delete_warning(courses.get_course(cid, self.path),
                                courses.count_linked_records(cid, db_path=self.path))
        self.assertIn("Nothing else is linked", msg)


class TimetableDataTests(Base):
    def seed(self):
        self.c1 = courses.add_course("CSC301", "Algorithms", 3, venue="LT1", db_path=self.path)
        self.c2 = courses.add_course("MTH201", "Linear Algebra", 2, db_path=self.path)
        timetable.add_slot(self.c1, "Wednesday", "14:00", "16:00", db_path=self.path)
        timetable.add_slot(self.c2, "Thursday", "08:00", "10:00", venue="Hall B",
                           db_path=self.path)

    def test_week_has_seven_days_in_order_with_today_marked(self):
        self.seed()
        week = td.build_week(NOW, self.path)
        self.assertEqual([d["day"] for d in week["days"]], timetable.DAYS)
        self.assertEqual(week["today"], "Wednesday")
        self.assertEqual([d["day"] for d in week["days"] if d["is_today"]], ["Wednesday"])
        self.assertEqual(week["total"], 2)

    def test_next_class_wording_comes_from_partition_a(self):
        self.seed()
        self.assertEqual(td.build_week(NOW, self.path)["next_text"],
                         "Next class: Today at 14:00  -  CSC301 Algorithms")
        later = datetime(2026, 10, 7, 15, 0)      # Wednesday class already started
        self.assertEqual(td.build_week(later, self.path)["next_text"],
                         "Next class: Tomorrow at 08:00  -  MTH201 Linear Algebra")

    def test_empty_timetable(self):
        week = td.build_week(NOW, self.path)
        self.assertEqual(week["next_text"], td.NO_CLASSES_TEXT)
        self.assertIsNone(week["next_class"])
        self.assertEqual(week["total"], 0)

    def test_course_choices_pairs(self):
        self.seed()
        self.assertEqual(td.course_choices(self.path),
                         [(f"CSC301 - Algorithms", self.c1), (f"MTH201 - Linear Algebra", self.c2)])

    def test_slot_text_helpers(self):
        self.seed()
        slot = timetable.get_classes_for_day("Wednesday", self.path)[0]
        self.assertEqual(td.time_range(slot), "14:00 - 16:00")
        self.assertEqual(td.slot_title(slot), "CSC301  Algorithms")

    def test_editable_venue_hides_inherited_course_venue(self):
        self.seed()
        inherited = timetable.get_classes_for_day("Wednesday", self.path)[0]
        own = timetable.get_classes_for_day("Thursday", self.path)[0]
        self.assertEqual(inherited["venue"], "LT1")           # Partition A falls back
        self.assertEqual(td.editable_venue(inherited, courses.get_course(self.c1, self.path)), "")
        self.assertEqual(td.editable_venue(own, courses.get_course(self.c2, self.path)), "Hall B")


class SettingsDataTests(Base):
    def test_gemini_status_never_exposes_the_key(self):
        off = sd.gemini_status(environ={})
        self.assertFalse(off["configured"])
        self.assertEqual(off["badge"], "Not set")
        self.assertIn("GEMINI_API_KEY", off["text"])
        on = sd.gemini_status(environ={"GEMINI_API_KEY": "SECRET-KEY-123"})
        self.assertTrue(on["configured"])
        self.assertEqual(on["badge"], "Key found")
        self.assertNotIn("SECRET-KEY-123", str(on))
        self.assertFalse(sd.gemini_status(environ={"GEMINI_API_KEY": "   "})["configured"])

    def test_load_settings_defaults(self):
        data = sd.load_settings(self.path, environ={})
        self.assertEqual(data["profile"], {"name": "", "academic_session": "", "semester": ""})
        self.assertEqual(data["threshold"], 75.0)
        self.assertEqual(data["db_file"], self.path)

    def test_save_profile_round_trip_and_validation(self):
        sd.save_profile({"name": " Ada Obi ", "academic_session": "2026/2027",
                         "semester": "First"}, self.path)
        self.assertEqual(profile.get_profile(self.path)["name"], "Ada Obi")
        self.assertEqual(sd.load_settings(self.path, environ={})["profile"]["semester"], "First")
        with self.assertRaises(ValueError) as ctx:
            sd.save_profile({"name": "  "}, self.path)
        self.assertEqual(str(ctx.exception), "Name is required.")

    def test_save_threshold_accepts_percent_sign_and_validates(self):
        self.assertEqual(sd.save_threshold("80", self.path), 80.0)
        self.assertEqual(sd.save_threshold(" 65% ", self.path), 65.0)
        self.assertEqual(settings.get_attendance_threshold(self.path), 65.0)
        for bad in ("abc", "", "101", "-5"):
            with self.assertRaises(ValueError):
                sd.save_threshold(bad, self.path)
        self.assertEqual(settings.get_attendance_threshold(self.path), 65.0)   # unchanged
        self.assertEqual(sd.threshold_text(65.0), "65%")
        self.assertEqual(sd.threshold_text(72.5), "72.5%")

    def test_backup_creates_a_readable_copy(self):
        profile.save_profile("Ada", db_path=self.path)
        target = sd.make_backup(self.path)
        self.assertTrue(os.path.exists(target))
        self.assertEqual(os.path.dirname(target), os.path.join(self.tmp.name, "backups"))
        self.assertEqual(profile.get_profile(target)["name"], "Ada")


if __name__ == "__main__":
    unittest.main()
