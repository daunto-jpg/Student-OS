"""B1: dashboard data builder against the REAL Partition A modules (no GUI needed)."""
import os
import tempfile
import unittest
from datetime import datetime

from student_os import assignments, attendance, courses, db, notes, profile, timetable
from student_os.ui import dashboard_data as dd

# Wednesday 7 Oct 2026, 10:30
NOW = datetime(2026, 10, 7, 10, 30)


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "t.db")
        db.init_db(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, now=NOW):
        return dd.build_dashboard(now=now, db_path=self.path)

    def seed(self):
        profile.save_profile("Ada Obi", "2026/2027", "First", db_path=self.path)
        self.c1 = courses.add_course("CSC301", "Algorithms", 3, venue="LT1", db_path=self.path)
        self.c2 = courses.add_course("MTH201", "Linear Algebra", 2, db_path=self.path)
        p = self.path
        timetable.add_slot(self.c1, "Wednesday", "08:00", "10:00", db_path=p)   # finished
        timetable.add_slot(self.c2, "Wednesday", "10:00", "12:00", db_path=p)   # ongoing
        timetable.add_slot(self.c1, "Wednesday", "14:00", "16:00", db_path=p)   # upcoming
        assignments.add_assignment(self.c1, "Late one", "2026-10-05", db_path=p)
        assignments.add_assignment(self.c1, "Today one", "2026-10-07", db_path=p)
        assignments.add_assignment(self.c2, "Soon one", "2026-10-09", db_path=p)
        assignments.add_assignment(self.c2, "Far one", "2026-11-30", db_path=p)
        done = assignments.add_assignment(self.c2, "Done one", "2026-10-01", db_path=p)
        assignments.mark_complete(done, db_path=p)
        for d, s in (("2026-10-01", "Present"), ("2026-10-02", "Absent"),
                     ("2026-10-03", "Absent"), ("2026-10-04", "Present")):
            attendance.record_attendance(self.c1, d, s, today=NOW.date(), db_path=p)
        notes.add_note(self.c1, "Sorting", "text", "exam, week 1", db_path=p)

    # -- pure helpers
    def test_greeting_by_hour(self):
        self.assertEqual(dd.greeting_for(5), "Good morning")
        self.assertEqual(dd.greeting_for(11), "Good morning")
        self.assertEqual(dd.greeting_for(12), "Good afternoon")
        self.assertEqual(dd.greeting_for(17), "Good evening")
        self.assertEqual(dd.greeting_for(23), "Hello")
        self.assertEqual(dd.greeting_for(3), "Hello")

    def test_describe_days_left(self):
        self.assertEqual(dd.describe_days_left(-1), "overdue by 1 day")
        self.assertEqual(dd.describe_days_left(-3), "overdue by 3 days")
        self.assertEqual(dd.describe_days_left(0), "due today")
        self.assertEqual(dd.describe_days_left(1), "due tomorrow")
        self.assertEqual(dd.describe_days_left(5), "due in 5 days")

    def test_class_status_boundaries(self):
        slot = {"start_time": "10:00", "end_time": "12:00"}
        self.assertEqual(dd.class_status(slot, "09:59"), "Upcoming")
        self.assertEqual(dd.class_status(slot, "10:00"), "Ongoing")
        self.assertEqual(dd.class_status(slot, "11:59"), "Ongoing")
        self.assertEqual(dd.class_status(slot, "12:00"), "Finished")

    def test_describe_next_class(self):
        base = {"start_time": "08:00", "day_of_week": "Monday"}
        self.assertEqual(dd.describe_next_class({**base, "days_until": 0}), "Today at 08:00")
        self.assertEqual(dd.describe_next_class({**base, "days_until": 1}), "Tomorrow at 08:00")
        self.assertEqual(dd.describe_next_class({**base, "days_until": 3}), "Monday at 08:00")
        self.assertEqual(dd.describe_next_class({**base, "days_until": 7}), "Next Monday at 08:00")

    # -- whole dashboard
    def test_empty_database(self):
        d = self.build()
        self.assertEqual(d["course_count"], 0)
        self.assertEqual(d["greeting"], "Good morning")      # no profile -> no name
        self.assertEqual(d["todays_classes"], [])
        self.assertIsNone(d["next_class"])
        self.assertEqual(d["assignments"]["pending"], 0)
        self.assertIsNone(d["attendance"]["overall"]["percentage"])
        self.assertEqual(d["attendance"]["standing"], "No records yet")
        self.assertEqual(d["recent_notes"], [])

    def test_populated_dashboard(self):
        self.seed()
        d = self.build()
        self.assertEqual(d["greeting"], "Good morning, Ada")
        self.assertEqual(d["date_text"], "Wednesday, 07 October 2026")
        self.assertEqual(d["course_count"], 2)
        self.assertEqual([c["status"] for c in d["todays_classes"]],
                         ["Finished", "Ongoing", "Upcoming"])
        self.assertEqual(d["next_class"]["start_time"], "14:00")
        self.assertEqual(d["next_class"]["when_text"], "Today at 14:00")

        a = d["assignments"]
        self.assertEqual(a["pending"], 4)           # completed one excluded
        self.assertEqual(a["overdue"], 1)
        self.assertEqual(a["due_today"], 1)
        self.assertEqual(a["due_soon"], 1)
        self.assertEqual([i["title"] for i in a["items"]],
                         ["Late one", "Today one", "Soon one", "Far one"])
        self.assertEqual(a["items"][0]["due_text"], "overdue by 2 days")

        att = d["attendance"]
        self.assertEqual(att["overall"]["percentage"], 50.0)
        self.assertEqual(att["standing"], "Below target")
        self.assertEqual([s["course_code"] for s in att["below"]], ["CSC301"])

        self.assertEqual(d["recent_notes"][0]["title"], "Sorting")
        self.assertEqual(len(d["recent_notes"][0]["updated_date"]), 10)

    def test_uses_injected_clock_not_real_time(self):
        self.seed()
        late = self.build(datetime(2026, 10, 7, 18, 0))
        self.assertEqual([c["status"] for c in late["todays_classes"]], ["Finished"] * 3)
        # only Wednesday classes exist, so after the last one the next is a week away
        self.assertEqual(late["next_class"]["days_until"], 7)
        self.assertEqual(late["next_class"]["when_text"], "Next Wednesday at 08:00")

    def test_assignment_list_is_capped(self):
        self.seed()
        cid = courses.add_course("PHY101", "Physics", 2, db_path=self.path)
        for i in range(10):
            assignments.add_assignment(cid, f"Lab {i}", "2026-12-01", db_path=self.path)
        a = self.build()["assignments"]
        self.assertEqual(len(a["items"]), dd.MAX_ASSIGNMENTS_SHOWN)
        self.assertEqual(a["pending"], 14)

    def test_recent_notes_capped(self):
        self.seed()
        for i in range(8):
            notes.add_note(self.c1, f"N{i}", "x", db_path=self.path)
        self.assertEqual(len(self.build()["recent_notes"]), dd.RECENT_NOTES)


if __name__ == "__main__":
    unittest.main()
