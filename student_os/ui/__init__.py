"""Partition B - GUI layer.

Rules for everything in this package:
  * Never write SQL. Call the Partition A modules (courses, timetable, ...).
  * Pass `db_path=self.app.db_path` to every Partition A call.
  * Anything that is pure logic (no widgets) lives in a module that does NOT
    import customtkinter, so it can be unit-tested without a display.

This file is intentionally empty of imports so `student_os.ui.dashboard_data`
can be imported on a machine with no GUI libraries.
"""