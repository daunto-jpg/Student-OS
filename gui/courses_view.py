"""Courses screen (Partition B, Member B2).

Add, edit, delete and search courses. All rules (required fields, unique code,
credit unit > 0, cascade delete) live in Partition A's courses.py - this file
only shows the data and passes the student's input back.
"""
import customtkinter as ctk

from student_os import courses
from student_os.ui import courses_data, dialogs
from student_os.ui.widgets import (Card, body_label, clear, muted_label, outline_button,
                                   page_header, primary_button)


class CoursesView(ctk.CTkFrame):
    """View contract: __init__(master, app) and refresh()."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid_columnconfigure(0, weight=1)
        page_header(top, "Courses", "Every timetable slot, assignment, attendance record "
                    "and note belongs to a course").grid(row=0, column=0, sticky="w")
        primary_button(top, "Add course", self.add_course).grid(row=0, column=1, sticky="e")
        top.pack(fill="x", padx=20, pady=(18, 8))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        self.search_box = ctk.CTkEntry(bar, height=34,
                                       placeholder_text="Search by code, name or lecturer")
        self.search_box.pack(side="left", fill="x", expand=True)
        self.search_box.bind("<KeyRelease>", lambda _event: self._render())
        self.count_label = muted_label(bar, "", size=13)
        self.count_label.pack(side="right", padx=(12, 0))
        bar.pack(fill="x", padx=20, pady=(0, 6))

        self.list_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_area.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # -- public ---------------------------------------------------------------
    def refresh(self):
        self._render()

    # -- drawing --------------------------------------------------------------
    def _render(self):
        query = self.search_box.get().strip()
        clear(self.list_area)
        try:
            items = courses_data.load_courses(query, self.app.db_path)
        except Exception as exc:     # keep the app alive; tell the student
            muted_label(self.list_area, f"Could not load courses: {exc}").pack(
                anchor="w", padx=12, pady=12)
            return
        self.count_label.configure(text=courses_data.count_text(len(items), query))
        if not items:
            muted_label(self.list_area, courses_data.empty_text(query), size=14).pack(
                anchor="w", padx=12, pady=12)
            return
        for course in items:
            self._course_card(course).pack(fill="x", padx=8, pady=5)

    def _course_card(self, course):
        card = Card(self.list_area, f"{course['code']}  -  {course['name']}")
        muted_label(card.body, courses_data.course_summary(course)).pack(anchor="w")
        if course["description"]:
            body_label(card.body, course["description"], size=13, wraplength=620
                       ).pack(anchor="w", pady=(6, 0))
        row = ctk.CTkFrame(card.body, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        outline_button(row, "Delete", lambda c=course: self.delete_course(c),
                       danger=True).pack(side="right")
        outline_button(row, "Edit", lambda c=course: self.edit_course(c)
                       ).pack(side="right", padx=(0, 8))
        return card

    # -- actions --------------------------------------------------------------
    @staticmethod
    def _fields(course=None):
        course = course or {}
        f = dialogs.Field
        return [
            f("code", "Course code", required=True, initial=course.get("code", ""),
              placeholder="e.g. CSC301"),
            f("name", "Course name", required=True, initial=course.get("name", "")),
            f("credit_unit", "Credit unit", required=True,
              initial=course.get("credit_unit", ""), placeholder="e.g. 3"),
            f("lecturer", "Lecturer", initial=course.get("lecturer", "")),
            f("venue", "Venue", initial=course.get("venue", "")),
            f("description", "Description", kind="multiline",
              initial=course.get("description", "")),
        ]

    def add_course(self):
        result = dialogs.FormDialog(
            self, "Add course", fields=self._fields(), submit_text="Add course",
            on_submit=lambda v: courses.add_course(**v, db_path=self.app.db_path),
        ).show()
        if result is not None:
            self.app.notify("Course added")
            self.refresh()

    def edit_course(self, course):
        result = dialogs.FormDialog(
            self, f"Edit {course['code']}", fields=self._fields(course),
            on_submit=lambda v: courses.update_course(course["id"], **v,
                                                      db_path=self.app.db_path),
        ).show()
        if result is not None:
            self.app.notify("Course updated")
            self.refresh()

    def delete_course(self, course):
        try:
            counts = courses.count_linked_records(course["id"], db_path=self.app.db_path)
        except Exception as exc:
            self.app.show_error(str(exc))
            return
        message = courses_data.delete_warning(course, counts)
        if not dialogs.confirm(self, "Delete course?", message, "Delete", danger=True):
            return
        try:
            courses.delete_course(course["id"], db_path=self.app.db_path)
        except LookupError as exc:       # already gone (e.g. deleted elsewhere)
            self.app.show_error(str(exc))
        else:
            self.app.notify(f"{course['code']} deleted")
        self.refresh()
