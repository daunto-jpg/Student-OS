"""B1: GUI wiring tests using tests/fake_ctk.py (no display, no customtkinter needed).

These check that our code runs and is wired correctly (navigation, plug-in
loading, error isolation, dashboard content, form validation flow).
They do NOT check appearance - see the manual checklist in the B1 document.
"""
import importlib
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime
from unittest import mock

from tests import fake_ctk
from tests.fake_ctk import find_buttons, texts

NOW = datetime(2026, 10, 7, 10, 30)


class GuiBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._patch = mock.patch.dict(sys.modules, {"customtkinter": fake_ctk.install()})
        cls._patch.start()
        for name in [m for m in sys.modules if m.startswith("student_os.ui")]:
            del sys.modules[name]
        cls.app_mod = importlib.import_module("student_os.ui.app")
        cls.dialogs = importlib.import_module("student_os.ui.dialogs")

    @classmethod
    def tearDownClass(cls):
        cls._patch.stop()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "gui.db")

    def tearDown(self):
        self.tmp.cleanup()

    def make_app(self, **kw):
        return self.app_mod.StudentOSApp(db_path=self.path, clock=lambda: NOW,
                                         ask_profile=False, **kw)


class TestShell(GuiBase):
    def test_starts_on_dashboard_with_all_nav_buttons(self):
        app = self.make_app()
        self.assertEqual(app.current, "dashboard")
        labels = texts(app)
        for item in self.app_mod.NAV_ITEMS:
            self.assertIn(item.label, labels)
        self.assertEqual(len(self.app_mod.NAV_ITEMS), 8)

    def test_clicking_sidebar_button_navigates(self):
        app = self.make_app()
        find_buttons(app, "Courses")[0].kw["command"]()
        self.assertEqual(app.current, "courses")
        self.assertEqual(app._nav_buttons["courses"].kw["fg_color"], self.app_mod.theme.SIDEBAR_ACTIVE)
        self.assertEqual(app._nav_buttons["dashboard"].kw["fg_color"], "transparent")

    def test_missing_screen_shows_placeholder(self):
        app = self.make_app()
        app.navigate("notes")
        self.assertIsInstance(app._views["notes"], self.app_mod.PlaceholderView)

    def test_unknown_screen_raises(self):
        with self.assertRaises(KeyError):
            self.make_app().navigate("nope")

    def test_real_screen_file_is_picked_up_by_name(self):
        """Dropping courses_view.py with a CoursesView class must need no change to app.py."""
        mod = types.ModuleType("student_os.ui.courses_view")

        class CoursesView(fake_ctk.Widget):
            def __init__(self, master, app):
                super().__init__(master)
                self.refreshed = 0
                self.app = app

            def refresh(self):
                self.refreshed += 1
        mod.CoursesView = CoursesView
        with mock.patch.dict(sys.modules, {"student_os.ui.courses_view": mod}):
            app = self.make_app()
            app.navigate("courses")
            app.navigate("dashboard")
            app.navigate("courses")
            view = app._views["courses"]
            self.assertIsInstance(view, CoursesView)
            self.assertIs(view.app, app)
            self.assertEqual(view.refreshed, 2)   # refreshed on every visit, built once

    def test_broken_screen_is_isolated(self):
        mod = types.ModuleType("student_os.ui.timetable_view")

        class TimetableView(fake_ctk.Widget):
            def __init__(self, master, app):
                raise RuntimeError("B2 bug")
        mod.TimetableView = TimetableView
        with mock.patch.dict(sys.modules, {"student_os.ui.timetable_view": mod}):
            app = self.make_app()
            app.navigate("timetable")
            self.assertIsInstance(app._views["timetable"], self.app_mod.ErrorView)
            self.assertTrue(any("B2 bug" in t for t in texts(app._views["timetable"])))
            app.navigate("dashboard")      # rest of the app still works
            self.assertEqual(app.current, "dashboard")

    def test_refresh_failure_shows_error_not_crash(self):
        mod = types.ModuleType("student_os.ui.settings_view")

        class SettingsView(fake_ctk.Widget):
            def __init__(self, master, app):
                super().__init__(master)

            def refresh(self):
                raise ValueError("boom")
        mod.SettingsView = SettingsView
        shown = []
        with mock.patch.dict(sys.modules, {"student_os.ui.settings_view": mod}):
            app = self.make_app()
            app.show_error = shown.append
            app.navigate("settings")
        self.assertEqual(len(shown), 1)
        self.assertIn("boom", shown[0])

    def test_notify_sets_and_schedules_clear(self):
        app = self.make_app()
        app.notify("Saved!", seconds=2)
        self.assertEqual(app.status.text, "Saved!")
        self.assertEqual(app.scheduled[-1][0], 2000)

    def test_identity_shown_in_sidebar(self):
        from student_os import profile
        app = self.make_app()
        self.assertEqual(app.identity_name.text, "Welcome")
        profile.save_profile("Ada Obi", "2026/2027", "First", db_path=self.path)
        app.refresh_identity()
        self.assertEqual(app.identity_name.text, "Ada Obi")
        self.assertEqual(app.identity_sub.text, "2026/2027 | First")

    def test_database_created_automatically(self):
        self.make_app()
        self.assertTrue(os.path.exists(self.path))

    def test_first_run_opens_non_cancelable_profile_dialog(self):
        shown = []
        original = self.dialogs.FormDialog.show
        self.dialogs.FormDialog.show = lambda d: shown.append(d)
        try:
            app = self.app_mod.StudentOSApp(db_path=self.path, clock=lambda: NOW, ask_profile=True)
            app.ensure_profile()
        finally:
            self.dialogs.FormDialog.show = original
        self.assertEqual(len(shown), 1)
        self.assertFalse(shown[0]._closable)
        self.assertEqual([f.name for f in shown[0].fields],
                         ["name", "academic_session", "semester"])
        # submitting it saves the profile through Partition A
        d = shown[0]
        d._inputs["name"].insert(0, "Ada Obi")
        d.submit()
        from student_os import profile
        self.assertEqual(profile.get_profile(self.path)["name"], "Ada Obi")


class TestDashboardView(GuiBase):
    def test_empty_dashboard_offers_to_add_course(self):
        app = self.make_app()
        t = texts(app._views["dashboard"])
        self.assertIn("Let's get you started", t)
        find_buttons(app._views["dashboard"], "Add a course")[0].kw["command"]()
        self.assertEqual(app.current, "courses")

    def test_dashboard_shows_real_data(self):
        from student_os import assignments, attendance, courses, notes, profile, timetable
        p = self.path
        self.make_app()  # creates schema
        profile.save_profile("Ada Obi", db_path=p)
        c = courses.add_course("CSC301", "Algorithms", 3, venue="LT1", db_path=p)
        timetable.add_slot(c, "Wednesday", "14:00", "16:00", db_path=p)
        assignments.add_assignment(c, "Problem set", "2026-10-05", priority="High", db_path=p)
        attendance.record_attendance(c, "2026-10-01", "Absent", today=NOW.date(), db_path=p)
        notes.add_note(c, "Sorting notes", "x", "exam", db_path=p)
        app = self.app_mod.StudentOSApp(db_path=p, clock=lambda: NOW, ask_profile=False)
        t = " || ".join(texts(app._views["dashboard"]))
        for expected in ("Good morning, Ada", "Wednesday, 07 October 2026", "CSC301  Algorithms",
                         "Today at 14:00", "Problem set", "Overdue", "overdue by 2 days",
                         "0.0% overall", "Below target", "Sorting notes", "CSC301  0.0%"):
            self.assertIn(expected, t)
        self.assertNotIn("Let's get you started", t)

    def test_refresh_redraws_without_duplicating(self):
        app = self.make_app()
        view = app._views["dashboard"]
        first = len(texts(view))
        view.refresh()
        view.refresh()
        self.assertEqual(len(texts(view)), first)

    def test_dashboard_survives_data_error(self):
        app = self.make_app()
        view = app._views["dashboard"]
        dash_mod = sys.modules["student_os.ui.dashboard"]
        with mock.patch.object(dash_mod, "build_dashboard", side_effect=RuntimeError("db locked")):
            view.refresh()
        self.assertTrue(any("db locked" in t for t in texts(view)))

    def test_card_links_navigate(self):
        from student_os import courses
        self.make_app()
        courses.add_course("CSC301", "Algorithms", 3, db_path=self.path)
        app = self.make_app()
        for link, target in (("Timetable", "timetable"), ("View all", "assignments"),
                             ("Details", "attendance"), ("All notes", "notes")):
            btn = [b for b in find_buttons(app._views["dashboard"], link)]
            self.assertTrue(btn, link)
            btn[0].kw["command"]()
            self.assertEqual(app.current, target)
            app.navigate("dashboard")


class TestFormDialog(GuiBase):
    def parent(self):
        return fake_ctk.Widget(None)

    def test_pure_helpers(self):
        d = self.dialogs
        self.assertEqual(d.normalize_choices(["a", "b"]), [("a", "a"), ("b", "b")])
        self.assertEqual(d.normalize_choices([("CSC301", 3)]), [("CSC301", 3)])
        f = [d.Field("a", "Alpha", required=True), d.Field("b", "Beta"),
             d.Field("c", "Gamma", required=True)]
        self.assertEqual(d.find_missing_required(f, {"a": " ", "b": "", "c": "x"}), ["Alpha"])
        self.assertEqual(d.find_missing_required(f, {"a": "1", "c": None}), ["Gamma"])
        with self.assertRaises(ValueError):
            d.Field("x", "X", kind="slider")

    def make(self, on_submit, **kw):
        d = self.dialogs
        fields = [d.Field("code", "Course code", required=True),
                  d.Field("credit_unit", "Credit unit", initial=3),
                  d.Field("priority", "Priority", kind="choice",
                          choices=["Low", "Medium", "High"], initial="High"),
                  d.Field("course_id", "Course", kind="choice",
                          choices=[("CSC301 - Algorithms", 7), ("MTH201 - Algebra", 9)], initial=9),
                  d.Field("description", "Description", kind="multiline")]
        return d.FormDialog(self.parent(), "Add", fields, on_submit, **kw)

    def test_collect_reads_values_and_choice_values(self):
        dlg = self.make(lambda v: None)
        dlg._inputs["code"].insert(0, "  csc301 ")
        dlg._inputs["description"].insert("1.0", "hello\n")
        vals = dlg.collect()
        self.assertEqual(vals["code"], "csc301")
        self.assertEqual(vals["credit_unit"], "3")        # initial value pre-filled
        self.assertEqual(vals["priority"], "High")        # initial applied
        self.assertEqual(vals["course_id"], 9)             # label -> value mapping
        self.assertEqual(vals["description"], "hello")

    def test_required_field_blocks_submit(self):
        called = []
        dlg = self.make(lambda v: called.append(v))
        dlg.submit()
        self.assertEqual(called, [])
        self.assertIn("Course code", dlg._error.text)
        self.assertFalse(dlg.destroyed)

    def test_partition_a_error_shown_inline_and_dialog_stays_open(self):
        def boom(values):
            raise ValueError("A course with code CSC301 already exists.")
        dlg = self.make(boom)
        dlg._inputs["code"].insert(0, "CSC301")
        dlg.submit()
        self.assertEqual(dlg._error.text, "A course with code CSC301 already exists.")
        self.assertFalse(dlg.destroyed)

    def test_unexpected_error_does_not_crash(self):
        dlg = self.make(lambda v: 1 / 0)
        dlg._inputs["code"].insert(0, "X")
        dlg.submit()
        self.assertIn("Unexpected error", dlg._error.text)
        self.assertFalse(dlg.destroyed)

    def test_success_closes_and_returns_value(self):
        dlg = self.make(lambda v: 42)
        dlg._inputs["code"].insert(0, "X")
        dlg.submit()
        self.assertTrue(dlg.destroyed)
        self.assertEqual(dlg.result, 42)

    def test_none_return_becomes_true(self):
        dlg = self.make(lambda v: None)
        dlg._inputs["code"].insert(0, "X")
        dlg.submit()
        self.assertIs(dlg.result, True)

    def test_cancel_returns_none(self):
        dlg = self.make(lambda v: 1)
        dlg.cancel()
        self.assertTrue(dlg.destroyed)
        self.assertIsNone(dlg.result)

    def test_non_cancelable_has_no_cancel_button(self):
        self.assertEqual(find_buttons(self.make(lambda v: 1, cancelable=False), "Cancel"), [])
        self.assertEqual(len(find_buttons(self.make(lambda v: 1), "Cancel")), 1)

    def test_empty_choice_list_does_not_crash(self):
        d = self.dialogs
        dlg = d.FormDialog(self.parent(), "x", [d.Field("c", "Course", kind="choice")],
                           lambda v: v)
        self.assertEqual(dlg.collect(), {"c": None})

    def test_confirm_returns_bool_of_button_value(self):
        d = self.dialogs
        with mock.patch.object(d._ButtonDialog, "show", return_value=True):
            self.assertIs(d.confirm(self.parent(), "t", "m"), True)
        with mock.patch.object(d._ButtonDialog, "show", return_value=None):
            self.assertIs(d.confirm(self.parent(), "t", "m"), False)

    def test_message_dialog_buttons(self):
        d = self.dialogs
        dlg = d._ButtonDialog(self.parent(), "t", "msg", [("No", False, "neutral"),
                                                          ("Delete", True, "danger")])
        find_buttons(dlg, "Delete")[0].kw["command"]()
        self.assertIs(dlg.result, True)


if __name__ == "__main__":
    unittest.main()
