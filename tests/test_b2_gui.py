"""B2: Courses, Timetable and Settings screens, wired to the REAL Partition A modules.

Uses tests/fake_ctk.py (no display). Forms are driven by filling the dialog's
inputs and calling submit(), exactly what the Save button does. These tests prove
logic and wiring, not appearance - see the manual checklist in the B2 guide.
"""
import importlib
import os
import sys
import unittest
from unittest import mock

from student_os import assignments, courses, profile, settings, timetable
from tests import fake_ctk
from tests import test_b1_gui_smoke as b1
from tests.fake_ctk import find_buttons, texts

NOW = b1.NOW      # Wednesday 7 Oct 2026, 10:30


class B2Base(b1.GuiBase):
    def setUp(self):
        super().setUp()
        self.app = self.make_app()           # creates the schema
        self.dlg = None
        self.info = []

    def run_form(self, action, entries=None, choices=None):
        """Run a view action that opens a FormDialog; fill it in and click Save."""
        def fake_show(dialog):
            for name, value in (entries or {}).items():
                dialog._inputs[name].insert(0, value)
            for name, label in (choices or {}).items():
                dialog._inputs[name].set(label)
            dialog.submit()
            self.dlg = dialog
            return dialog.result
        with mock.patch.object(self.dialogs.FormDialog, "show", fake_show):
            action()

    def confirm_with(self, answer):
        seen = []

        def fake_confirm(parent, title, message, *a, **kw):
            seen.append(message)
            return answer
        return mock.patch.object(self.dialogs, "confirm", fake_confirm), seen

    def view(self, key):
        self.app.navigate(key)
        return self.app._views[key]


class TestCoursesView(B2Base):
    def test_real_screen_is_loaded_not_placeholder(self):
        self.assertEqual(type(self.view("courses")).__name__, "CoursesView")

    def test_empty_state(self):
        t = texts(self.view("courses"))
        self.assertIn(self.cd().empty_text(), t)

    def cd(self):
        return sys.modules["student_os.ui.courses_data"]

    def test_lists_courses_with_details_and_count(self):
        courses.add_course("CSC301", "Algorithms", 3, lecturer="Dr Musa", venue="LT1",
                           description="Sorting and graphs", db_path=self.path)
        courses.add_course("MTH201", "Linear Algebra", 2, db_path=self.path)
        view = self.view("courses")
        t = " || ".join(texts(view))
        for expected in ("CSC301  -  Algorithms", "Dr Musa  |  LT1  |  3 credit units",
                         "Sorting and graphs", "MTH201  -  Linear Algebra", "2 credit units"):
            self.assertIn(expected, t)
        self.assertEqual(view.count_label.text, "2 courses")

    def test_search_filters_live(self):
        courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        courses.add_course("MTH201", "Linear Algebra", 2, db_path=self.path)
        view = self.view("courses")
        view.search_box._value = "csc"
        view._render()
        t = " || ".join(texts(view))
        self.assertIn("CSC301", t)
        self.assertNotIn("MTH201", t)
        self.assertEqual(view.count_label.text, "1 match")
        view.search_box._value = "zzz"
        view._render()
        self.assertIn('No courses match "zzz".', texts(view))

    def test_add_course_saves_via_partition_a_and_refreshes(self):
        view = self.view("courses")
        self.run_form(view.add_course, entries={
            "code": "csc301", "name": "Algorithms", "credit_unit": "3", "lecturer": "Dr Musa"})
        saved = courses.list_courses(self.path)
        self.assertEqual([(c["code"], c["credit_unit"]) for c in saved], [("CSC301", 3)])
        self.assertEqual(self.app.status.text, "Course added")
        self.assertIn("CSC301  -  Algorithms", texts(view))

    def test_duplicate_code_error_shown_inline_dialog_stays_open(self):
        courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        view = self.view("courses")
        self.run_form(view.add_course, entries={
            "code": "CSC301", "name": "Other", "credit_unit": "2"})
        self.assertEqual(self.dlg._error.text, "A course with code CSC301 already exists.")
        self.assertFalse(self.dlg.destroyed)
        self.assertEqual(len(courses.list_courses(self.path)), 1)
        self.assertEqual(self.app.status.text, "")

    def test_bad_input_messages_come_from_partition_a(self):
        view = self.view("courses")
        self.run_form(view.add_course, entries={"code": "X1", "name": "N", "credit_unit": "abc"})
        self.assertEqual(self.dlg._error.text, "Credit unit must be a whole number.")
        self.run_form(view.add_course, entries={"code": "X1", "name": "N", "credit_unit": "0"})
        self.assertEqual(self.dlg._error.text, "Credit unit must be greater than zero.")
        self.run_form(view.add_course, entries={"code": "X1"})       # name + credit left empty
        self.assertIn("Course name", self.dlg._error.text)
        self.assertEqual(courses.list_courses(self.path), [])

    def test_edit_prefills_and_updates(self):
        cid = courses.add_course("CSC301", "Algorithms", 3, lecturer="Dr Musa", db_path=self.path)
        view = self.view("courses")
        course = courses.get_course(cid, self.path)
        self.run_form(lambda: view.edit_course(course), entries={"lecturer": "Prof Bello"})
        self.assertEqual({f.name: f.initial for f in self.dlg.fields}["code"], "CSC301")
        self.assertEqual(courses.get_course(cid, self.path)["lecturer"], "Prof Bello")
        self.assertEqual(courses.get_course(cid, self.path)["credit_unit"], 3)   # untouched
        self.assertEqual(self.app.status.text, "Course updated")

    def test_edit_to_existing_code_is_refused_inline(self):
        courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        other = courses.add_course("MTH201", "Algebra", 2, db_path=self.path)
        view = self.view("courses")
        self.run_form(lambda: view.edit_course(courses.get_course(other, self.path)),
                      entries={"code": "CSC301"})
        self.assertIn("already exists", self.dlg._error.text)
        self.assertEqual(courses.get_course(other, self.path)["code"], "MTH201")

    def test_delete_warns_with_counts_then_cascades(self):
        cid = courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        timetable.add_slot(cid, "Monday", "08:00", "10:00", db_path=self.path)
        assignments.add_assignment(cid, "A1", "2026-10-20", db_path=self.path)
        view = self.view("courses")
        patch, seen = self.confirm_with(True)
        with patch:
            view.delete_course(courses.get_course(cid, self.path))
        self.assertIn("1 class slot", seen[0])
        self.assertIn("1 assignment", seen[0])
        self.assertEqual(courses.list_courses(self.path), [])
        self.assertEqual(assignments.list_assignments(db_path=self.path), [])   # cascaded
        self.assertEqual(self.app.status.text, "CSC301 deleted")

    def test_delete_cancelled_keeps_everything(self):
        cid = courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        view = self.view("courses")
        patch, _ = self.confirm_with(False)
        with patch:
            view.delete_course(courses.get_course(cid, self.path))
        self.assertEqual(len(courses.list_courses(self.path)), 1)

    def test_delete_of_already_removed_course_shows_error_not_crash(self):
        cid = courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        view = self.view("courses")
        stale = courses.get_course(cid, self.path)
        courses.delete_course(cid, self.path)
        shown = []
        self.app.show_error = shown.append
        patch, _ = self.confirm_with(True)
        with patch:
            view.delete_course(stale)
        self.assertEqual(len(shown), 1)

    def test_row_buttons_are_wired(self):
        cid = courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        view = self.view("courses")
        edits, deletes = find_buttons(view, "Edit"), find_buttons(view, "Delete")
        self.assertEqual((len(edits), len(deletes)), (1, 1))
        called = []
        view.edit_course = lambda c: called.append(("edit", c["id"]))
        view.delete_course = lambda c: called.append(("delete", c["id"]))
        view.refresh()                      # re-draw so the buttons bind the patched methods
        find_buttons(view, "Edit")[0].kw["command"]()
        find_buttons(view, "Delete")[0].kw["command"]()
        self.assertEqual(called, [("edit", cid), ("delete", cid)])

    def test_dashboard_add_course_button_lands_on_real_screen(self):
        find_buttons(self.app._views["dashboard"], "Add a course")[0].kw["command"]()
        self.assertEqual(self.app.current, "courses")
        self.assertEqual(type(self.app._views["courses"]).__name__, "CoursesView")

    def test_load_failure_shows_message(self):
        view = self.view("courses")
        mod = sys.modules["student_os.ui.courses_view"]
        with mock.patch.object(mod.courses_data, "load_courses",
                               side_effect=RuntimeError("db locked")):
            view.refresh()
        self.assertTrue(any("db locked" in t for t in texts(view)))


class TestTimetableView(B2Base):
    def seed(self):
        self.c1 = courses.add_course("CSC301", "Algorithms", 3, venue="LT1", db_path=self.path)
        self.c2 = courses.add_course("MTH201", "Linear Algebra", 2, db_path=self.path)
        self.slot = timetable.add_slot(self.c1, "Wednesday", "14:00", "16:00", db_path=self.path)

    def test_empty_week(self):
        view = self.view("timetable")
        t = texts(view)
        self.assertIn("No classes scheduled yet.", t)
        self.assertEqual(t.count("No classes"), 7)

    def test_shows_week_with_today_and_next_class(self):
        self.seed()
        timetable.add_slot(self.c2, "Thursday", "08:00", "10:00", venue="Hall B",
                           db_path=self.path)
        view = self.view("timetable")
        t = " || ".join(texts(view))
        for expected in ("Wednesday  (today)", "Monday", "Sunday", "14:00 - 16:00",
                         "CSC301  Algorithms", "LT1", "08:00 - 10:00", "Hall B",
                         "Next class: Today at 14:00  -  CSC301 Algorithms"):
            self.assertIn(expected, t)
        self.assertEqual(view.next_label.text, "Next class: Today at 14:00  -  CSC301 Algorithms")

    def test_add_class_saves_through_partition_a(self):
        self.seed()
        view = self.view("timetable")
        self.run_form(view.add_class,
                      entries={"start_time": "08:00", "end_time": "10:00", "venue": "Hall C"},
                      choices={"course_id": "MTH201 - Linear Algebra", "day_of_week": "Friday"})
        slots = timetable.get_classes_for_day("Friday", self.path)
        self.assertEqual([(s["course_code"], s["start_time"], s["venue"]) for s in slots],
                         [("MTH201", "08:00", "Hall C")])
        self.assertEqual(self.app.status.text, "Class added")
        self.assertIn("Hall C", texts(view))

    def test_clash_is_reported_inline(self):
        self.seed()
        view = self.view("timetable")
        self.run_form(view.add_class,
                      entries={"start_time": "15:00", "end_time": "17:00"},
                      choices={"course_id": "MTH201 - Linear Algebra",
                               "day_of_week": "Wednesday"})
        self.assertEqual(self.dlg._error.text,
                         "This clashes with CSC301 on Wednesday (14:00-16:00).")
        self.assertFalse(self.dlg.destroyed)
        self.assertEqual(len(timetable.get_classes_for_day("Wednesday", self.path)), 1)

    def test_bad_time_format_is_reported_inline(self):
        self.seed()
        view = self.view("timetable")
        self.run_form(view.add_class, entries={"start_time": "8am", "end_time": "10:00"})
        self.assertIn("24-hour HH:MM", self.dlg._error.text)
        self.run_form(view.add_class, entries={"start_time": "11:00", "end_time": "10:00"})
        self.assertEqual(self.dlg._error.text, "Start time must be before end time.")

    def test_default_day_in_add_form_is_today(self):
        self.seed()
        view = self.view("timetable")
        self.run_form(view.add_class, entries={"start_time": "18:00", "end_time": "19:00"})
        self.assertEqual(len(timetable.get_classes_for_day("Wednesday", self.path)), 2)

    def test_add_class_without_courses_guides_to_courses(self):
        view = self.view("timetable")
        shown = []
        with mock.patch.object(self.dialogs, "show_info", lambda p, m, **k: shown.append(m)):
            view.add_class()
        self.assertIn("Add a course first", shown[0])
        self.assertEqual(self.app.current, "courses")

    def test_edit_slot_updates_and_keeps_course(self):
        self.seed()
        view = self.view("timetable")
        slot = timetable.get_slot(self.slot, self.path)
        self.run_form(lambda: view.edit_slot(slot), entries={"end_time": "17:00"},
                      choices={"day_of_week": "Thursday"})
        updated = timetable.get_slot(self.slot, self.path)
        self.assertEqual((updated["day_of_week"], updated["end_time"], updated["course_code"]),
                         ("Thursday", "17:00", "CSC301"))
        self.assertEqual(self.app.status.text, "Class updated")

    def test_editing_does_not_freeze_the_course_venue_into_the_slot(self):
        self.seed()
        view = self.view("timetable")
        slot = timetable.get_slot(self.slot, self.path)
        self.assertEqual(slot["venue"], "LT1")                 # inherited from the course
        self.run_form(lambda: view.edit_slot(slot), entries={"end_time": "17:00"})
        courses.update_course(self.c1, venue="LT2", db_path=self.path)
        self.assertEqual(timetable.get_slot(self.slot, self.path)["venue"], "LT2")   # still follows

    def test_edit_clash_with_other_slot_is_refused(self):
        self.seed()
        other = timetable.add_slot(self.c2, "Wednesday", "16:00", "18:00", db_path=self.path)
        view = self.view("timetable")
        self.run_form(lambda: view.edit_slot(timetable.get_slot(other, self.path)),
                      entries={"start_time": "15:00"})
        self.assertIn("clashes with CSC301", self.dlg._error.text)

    def test_delete_slot_confirm_and_cancel(self):
        self.seed()
        view = self.view("timetable")
        slot = timetable.get_slot(self.slot, self.path)
        patch, seen = self.confirm_with(False)
        with patch:
            view.delete_slot(slot)
        self.assertEqual(len(timetable.get_classes_for_day("Wednesday", self.path)), 1)
        patch, seen = self.confirm_with(True)
        with patch:
            view.delete_slot(slot)
        self.assertIn("CSC301 on Wednesday (14:00 - 16:00)", seen[0])
        self.assertEqual(timetable.get_classes_for_day("Wednesday", self.path), [])
        self.assertEqual(self.app.status.text, "Class deleted")

    def test_dashboard_timetable_link_opens_real_screen(self):
        find_buttons(self.app._views["dashboard"], "Timetable")[0].kw["command"]()
        self.assertEqual(type(self.app._views["timetable"]).__name__, "TimetableView")

    def test_refresh_does_not_duplicate_cards(self):
        self.seed()
        view = self.view("timetable")
        first = len(texts(view))
        view.refresh()
        view.refresh()
        self.assertEqual(len(texts(view)), first)


class TestSettingsView(B2Base):
    def setUp(self):
        super().setUp()
        mod = importlib.import_module("student_os.ui.settings_data")
        self._patch_dotenv = mock.patch.object(mod, "_load_dotenv", lambda: None)
        self._patch_dotenv.start()
        self._env = mock.patch.dict(os.environ, {}, clear=True)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._patch_dotenv.stop()
        super().tearDown()

    def entries(self, view):
        return {k: e.get() for k, e in view.profile_entries.items()}

    def test_real_screen_is_loaded(self):
        self.assertEqual(type(self.view("settings")).__name__, "SettingsView")

    def test_refresh_shows_saved_values(self):
        profile.save_profile("Ada Obi", "2026/2027", "First", db_path=self.path)
        settings.set_attendance_threshold(70, self.path)
        view = self.view("settings")
        self.assertEqual(self.entries(view), {"name": "Ada Obi",
                                              "academic_session": "2026/2027",
                                              "semester": "First"})
        self.assertEqual(view.threshold_entry.get(), "70")

    def test_save_profile_updates_database_and_sidebar(self):
        view = self.view("settings")
        view.profile_entries["name"].insert(0, "Ada Obi")
        view.profile_entries["semester"].insert(0, "Second")
        view.save_profile()
        saved = profile.get_profile(self.path)
        self.assertEqual((saved["name"], saved["semester"]), ("Ada Obi", "Second"))
        self.assertEqual(self.app.identity_name.text, "Ada Obi")
        self.assertEqual(self.app.status.text, "Profile saved")
        self.assertEqual(view.profile_message.text, "")

    def test_empty_name_shows_partition_a_message(self):
        view = self.view("settings")
        view.save_profile()
        self.assertEqual(view.profile_message.text, "Name is required.")
        self.assertIsNone(profile.get_profile(self.path))

    def test_threshold_saved_and_changes_attendance_warning(self):
        from student_os import attendance
        cid = courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        for d, s in (("2026-10-01", "Present"), ("2026-10-02", "Absent")):
            attendance.record_attendance(cid, d, s, today=NOW.date(), db_path=self.path)
        self.assertEqual(len(attendance.get_courses_below_threshold(db_path=self.path)), 1)  # 50% < 75%
        view = self.view("settings")
        view.threshold_entry.insert(0, "40%")                     # '%' sign is accepted
        view.save_threshold()
        self.assertEqual(settings.get_attendance_threshold(self.path), 40.0)
        self.assertEqual(attendance.get_courses_below_threshold(db_path=self.path), [])
        self.assertEqual(self.app.status.text, "Attendance warning set to 40%")
        self.assertEqual(view.threshold_message.text, "")

    def test_invalid_threshold_shows_message_and_keeps_old_value(self):
        view = self.view("settings")
        for bad in ("abc", "150"):
            view.threshold_entry.insert(0, bad)
            view.save_threshold()
            self.assertIn("between 0 and 100", view.threshold_message.text)
        self.assertEqual(settings.get_attendance_threshold(self.path), 75.0)

    def test_gemini_status_without_key(self):
        t = " || ".join(texts(self.view("settings")))
        self.assertIn("Not set", t)
        self.assertIn("GEMINI_API_KEY", t)

    def test_gemini_status_with_key_never_displays_it(self):
        os.environ["GEMINI_API_KEY"] = "SUPER-SECRET-VALUE"
        t = " || ".join(texts(self.view("settings")))
        self.assertIn("Key found", t)
        self.assertNotIn("SUPER-SECRET-VALUE", t)

    def test_backup_creates_file_and_reports_its_location(self):
        profile.save_profile("Ada", db_path=self.path)
        view = self.view("settings")
        shown = []
        with mock.patch.object(self.dialogs, "show_info", lambda p, m, **k: shown.append(m)):
            view.backup()
        self.assertEqual(len(shown), 1)
        path = shown[0].split("\n", 1)[1]
        self.assertTrue(os.path.exists(path))
        self.assertEqual(profile.get_profile(path)["name"], "Ada")
        self.assertEqual(self.app.status.text, "Backup created")

    def test_backup_failure_is_reported_not_raised(self):
        view = self.view("settings")
        mod = sys.modules["student_os.ui.settings_view"]
        with mock.patch.object(mod.settings_data, "make_backup",
                               side_effect=OSError("disk full")):
            view.backup()
        self.assertIn("disk full", view.backup_message.text)

    def test_database_location_is_shown(self):
        self.assertIn(self.path, " || ".join(texts(self.view("settings"))))

    def test_refresh_does_not_duplicate_widgets(self):
        view = self.view("settings")
        first = len(texts(view))
        view.refresh()
        view.refresh()
        self.assertEqual(len(texts(view)), first)


class TestAllB2ScreensTogether(B2Base):
    def test_sidebar_opens_each_b2_screen_and_shortcuts_work(self):
        for key, cls in (("courses", "CoursesView"), ("timetable", "TimetableView"),
                         ("settings", "SettingsView")):
            find_buttons(self.app, self.app_mod.NAV_BY_KEY[key].label)[0].kw["command"]()
            self.assertEqual(self.app.current, key)
            self.assertEqual(type(self.app._views[key]).__name__, cls)


if __name__ == "__main__":
    unittest.main()
