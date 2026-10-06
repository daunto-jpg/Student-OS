import os
import tempfile
import unittest
from datetime import datetime

from student_os import courses, db, timetable


class A2Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.db")
        db.init_db(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def course(self, code="CSC301", **kw):
        return courses.add_course(code, kw.pop("name", "Algorithms"), kw.pop("credit", 3),
                                  db_path=self.path, **kw)


class TestCourses(A2Base):
    def test_add_and_get(self):
        cid = self.course("csc 301".replace(" ", ""), lecturer="Dr A", venue="LT1")
        c = courses.get_course(cid, self.path)
        self.assertEqual(c["code"], "CSC301")
        self.assertEqual(c["lecturer"], "Dr A")

    def test_validation(self):
        bad = [("", "N", 3), ("C1", "", 3), ("C1", "N", 0), ("C1", "N", -2), ("C1", "N", "abc")]
        for code, name, cu in bad:
            with self.assertRaises(ValueError, msg=(code, name, cu)):
                courses.add_course(code, name, cu, db_path=self.path)

    def test_duplicate_code_friendly_error(self):
        self.course("CSC301")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.course("csc301")

    def test_list_is_sorted(self):
        self.course("MTH201")
        self.course("CSC301")
        self.assertEqual([c["code"] for c in courses.list_courses(self.path)],
                         ["CSC301", "MTH201"])

    def test_search(self):
        self.course("CSC301", name="Algorithms", lecturer="Dr Bello")
        self.course("MTH201", name="Linear Algebra")
        self.assertEqual(len(courses.search_courses("alg", self.path)), 2)
        self.assertEqual(len(courses.search_courses("bello", self.path)), 1)
        self.assertEqual(len(courses.search_courses("", self.path)), 2)
        self.assertEqual(courses.search_courses("zzz", self.path), [])

    def test_update(self):
        cid = self.course()
        c = courses.update_course(cid, name="Advanced Algorithms", credit_unit=4,
                                  db_path=self.path)
        self.assertEqual((c["name"], c["credit_unit"]), ("Advanced Algorithms", 4))

    def test_update_rejects_clash_unknown_field_and_missing(self):
        a, _ = self.course("CSC301"), self.course("MTH201")
        with self.assertRaisesRegex(ValueError, "already exists"):
            courses.update_course(a, code="MTH201", db_path=self.path)
        with self.assertRaises(ValueError):
            courses.update_course(a, id=99, db_path=self.path)
        with self.assertRaises(LookupError):
            courses.update_course(999, name="x", db_path=self.path)

    def test_update_keeping_same_code_is_fine(self):
        cid = self.course("CSC301")
        courses.update_course(cid, code="csc301", venue="LT2", db_path=self.path)

    def test_delete_cascades_and_count(self):
        cid = self.course()
        timetable.add_slot(cid, "Monday", "08:00", "10:00", db_path=self.path)
        self.assertEqual(courses.count_linked_records(cid, self.path)["timetable"], 1)
        courses.delete_course(cid, self.path)
        self.assertIsNone(courses.get_course(cid, self.path))
        self.assertEqual(sum(len(timetable.get_weekly_timetable(self.path)[d])
                             for d in timetable.DAYS), 0)

    def test_delete_missing(self):
        with self.assertRaises(LookupError):
            courses.delete_course(999, self.path)


class TestTimetable(A2Base):
    def slot(self, cid, day="Monday", s="08:00", e="10:00", **kw):
        return timetable.add_slot(cid, day, s, e, db_path=self.path, **kw)

    def test_add_and_get_with_course_info(self):
        cid = self.course(venue="LT1")
        sid = self.slot(cid)
        s = timetable.get_slot(sid, self.path)
        self.assertEqual((s["course_code"], s["day_of_week"], s["venue"]),
                         ("CSC301", "Monday", "LT1"))

    def test_slot_venue_overrides_course_venue(self):
        cid = self.course(venue="LT1")
        s = timetable.get_slot(self.slot(cid, venue="Lab 2"), self.path)
        self.assertEqual(s["venue"], "Lab 2")

    def test_validation(self):
        cid = self.course()
        for args in [("Funday", "08:00", "10:00"), ("Monday", "8:00", "10:00"),
                     ("Monday", "08:00", "25:00"), ("Monday", "10:00", "08:00"),
                     ("Monday", "08:00", "08:00"), ("Monday", "", "10:00")]:
            with self.assertRaises(ValueError, msg=args):
                timetable.add_slot(cid, *args, db_path=self.path)

    def test_day_name_is_normalised(self):
        cid = self.course()
        s = timetable.get_slot(self.slot(cid, day="  monday "), self.path)
        self.assertEqual(s["day_of_week"], "Monday")

    def test_unknown_course(self):
        with self.assertRaises(LookupError):
            timetable.add_slot(999, "Monday", "08:00", "09:00", db_path=self.path)

    def test_overlap_rejected_but_touching_allowed(self):
        a, b = self.course("CSC301"), self.course("MTH201")
        self.slot(a, "Monday", "08:00", "10:00")
        with self.assertRaisesRegex(ValueError, "clashes with CSC301"):
            self.slot(b, "Monday", "09:00", "11:00")
        self.slot(b, "Monday", "10:00", "12:00")
        self.slot(b, "Tuesday", "08:00", "10:00")

    def test_update_slot_can_keep_own_time(self):
        cid = self.course()
        sid = self.slot(cid, "Monday", "08:00", "10:00")
        s = timetable.update_slot(sid, "Monday", "08:00", "11:00", db_path=self.path)
        self.assertEqual(s["end_time"], "11:00")

    def test_update_and_delete_missing(self):
        with self.assertRaises(LookupError):
            timetable.update_slot(999, "Monday", "08:00", "09:00", db_path=self.path)
        with self.assertRaises(LookupError):
            timetable.delete_slot(999, self.path)

    def test_delete_slot(self):
        sid = self.slot(self.course())
        timetable.delete_slot(sid, self.path)
        self.assertIsNone(timetable.get_slot(sid, self.path))

    def test_weekly_timetable_has_every_day_sorted(self):
        a, b = self.course("CSC301"), self.course("MTH201")
        self.slot(b, "Monday", "12:00", "13:00")
        self.slot(a, "Monday", "08:00", "10:00")
        week = timetable.get_weekly_timetable(self.path)
        self.assertEqual(list(week), timetable.DAYS)
        self.assertEqual([s["start_time"] for s in week["Monday"]], ["08:00", "12:00"])
        self.assertEqual(week["Sunday"], [])


class TestTodayAndNext(A2Base):
    def setUp(self):
        super().setUp()
        a, b = self.course("CSC301"), self.course("MTH201")
        timetable.add_slot(a, "Monday", "08:00", "10:00", db_path=self.path)
        timetable.add_slot(b, "Monday", "14:00", "16:00", db_path=self.path)
        timetable.add_slot(a, "Wednesday", "09:00", "11:00", db_path=self.path)

    def at(self, y, m, d, hh, mm):
        return datetime(y, m, d, hh, mm)

    def test_todays_classes(self):
        got = timetable.get_todays_classes(self.at(2026, 10, 5, 7, 0), self.path)
        self.assertEqual([s["course_code"] for s in got], ["CSC301", "MTH201"])
        self.assertEqual(timetable.get_todays_classes(self.at(2026, 10, 6, 7, 0), self.path), [])

    def test_next_class_later_today(self):
        n = timetable.get_next_class(self.at(2026, 10, 5, 10, 30), self.path)
        self.assertEqual((n["course_code"], n["is_today"], n["days_until"]), ("MTH201", True, 0))

    def test_class_in_progress_is_not_next(self):
        n = timetable.get_next_class(self.at(2026, 10, 5, 8, 30), self.path)
        self.assertEqual(n["course_code"], "MTH201")

    def test_next_class_rolls_to_later_day(self):
        n = timetable.get_next_class(self.at(2026, 10, 5, 17, 0), self.path)
        self.assertEqual((n["day_of_week"], n["is_today"], n["days_until"]), ("Wednesday", False, 2))

    def test_next_class_wraps_to_next_week(self):
        n = timetable.get_next_class(self.at(2026, 10, 7, 12, 0), self.path)
        self.assertEqual((n["day_of_week"], n["days_until"]), ("Monday", 5))

    def test_empty_timetable(self):
        empty = os.path.join(self.tmp.name, "empty.db")
        db.init_db(empty)
        self.assertIsNone(timetable.get_next_class(self.at(2026, 10, 5, 9, 0), empty))


if __name__ == "__main__":
    unittest.main()
