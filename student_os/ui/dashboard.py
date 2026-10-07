import customtkinter as ctk

from student_os.ui.dashboard_data import build_dashboard
from student_os.ui.widgets import Badge, Card, StatTile, body_label, clear, muted_label, primary_button


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh(self):
        clear(self.scroll)
        try:
            data = build_dashboard(now=self.app.now(), db_path=self.app.db_path)
        except Exception as exc:
            muted_label(self.scroll, f"Could not load the dashboard: {exc}").pack(
                padx=16, pady=16
            )
            return

        body_label(self.scroll, data["greeting"], size=28, weight="bold").pack(
            anchor="w", padx=16, pady=(12, 0)
        )
        muted_label(self.scroll, data["date_text"]).pack(anchor="w", padx=16)

        if data["course_count"] == 0:
            card = Card(self.scroll, "Let's get you started")
            card.pack(fill="x", padx=12, pady=12)
            body_label(
                card.body,
                "Add your first course, then your timetable, assignments, attendance and notes will fill this page in.",
            ).pack(anchor="w")
            primary_button(
                card.body, "Add a course", lambda: self.app.navigate("courses")
            ).pack(anchor="w", pady=(10, 0))
            return

        stats = ctk.CTkFrame(self.scroll, fg_color="transparent")
        stats.pack(fill="x", padx=12, pady=12)
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stats")
        a = data["assignments"]
        overall = data["attendance"]["overall"]
        pct = "—" if overall["percentage"] is None else f'{overall["percentage"]:.1f}%'
        for col, tile in enumerate(
            (
                StatTile(stats, "Courses", data["course_count"]),
                StatTile(stats, "Pending", a["pending"], f'{a["overdue"]} overdue'),
                StatTile(stats, "Due soon", a["due_soon"], f'{a["due_today"]} due today'),
                StatTile(stats, "Attendance", pct, data["attendance"]["standing"]),
            )
        ):
            tile.grid(row=0, column=col, sticky="ew", padx=4)

        classes = Card(self.scroll, "Today's classes", "Timetable",
                       lambda: self.app.navigate("timetable"))
        classes.pack(fill="x", padx=12, pady=6)
        if not data["todays_classes"]:
            muted_label(classes.body, "No classes scheduled today.").pack(anchor="w")
        else:
            for slot in data["todays_classes"]:
                row = ctk.CTkFrame(classes.body, fg_color="transparent")
                row.pack(fill="x", pady=3)
                body_label(
                    row,
                    f'{slot["start_time"]} - {slot["end_time"]}   {slot["course_code"]}  {slot["course_name"]}',
                ).pack(side="left")
                Badge(row, slot["status"]).pack(side="right")
        if data["next_class"]:
            muted_label(
                classes.body,
                f'Next class: {data["next_class"]["when_text"]}  -  {data["next_class"]["course_code"]} {data["next_class"]["course_name"]}',
            ).pack(anchor="w", pady=(7, 0))

        assignments_card = Card(self.scroll, "Assignments", "View all",
                                lambda: self.app.navigate("assignments"))
        assignments_card.pack(fill="x", padx=12, pady=6)
        if not a["items"]:
            muted_label(assignments_card.body, "No pending assignments.").pack(anchor="w")
        else:
            for item in a["items"]:
                row = ctk.CTkFrame(assignments_card.body, fg_color="transparent")
                row.pack(fill="x", pady=3)
                body_label(row, f'{item["course_code"]}  {item["title"]}').pack(side="left")
                Badge(row, item["state"]).pack(side="right")
                muted_label(row, item["due_text"], size=12).pack(side="right", padx=(0, 8))

        att_card = Card(self.scroll, "Attendance", "Details",
                        lambda: self.app.navigate("attendance"))
        att_card.pack(fill="x", padx=12, pady=6)
        muted_label(
            att_card.body,
            f'{pct} overall  •  {data["attendance"]["standing"]}',
        ).pack(anchor="w")
        if data["attendance"]["below"]:
            body_label(
                att_card.body,
                "Courses below target: "
                + ", ".join(s["course_code"] for s in data["attendance"]["below"]),
            ).pack(anchor="w", pady=(5, 0))

        notes_card = Card(self.scroll, "Recent notes", "All notes",
                          lambda: self.app.navigate("notes"))
        notes_card.pack(fill="x", padx=12, pady=6)
        if not data["recent_notes"]:
            muted_label(notes_card.body, "No notes yet.").pack(anchor="w")
        else:
            for note in data["recent_notes"]:
                body_label(
                    notes_card.body,
                    f'{note["course_code"]}  {note["title"]}',
                ).pack(anchor="w", pady=2)
