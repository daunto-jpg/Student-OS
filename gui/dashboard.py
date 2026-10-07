"""Dashboard screen (Partition B, Member B1).

Draws the dict from dashboard_data.build_dashboard(). All numbers are computed
in Python by Partition A - this file only lays them out.
"""
import customtkinter as ctk

from student_os.ui import theme
from student_os.ui.dashboard_data import build_dashboard
from student_os.ui.theme import font
from student_os.ui.widgets import (Badge, Card, StatTile, body_label, clear, divider,
                                   muted_label)


class DashboardView(ctk.CTkFrame):
    """View contract: __init__(master, app) and refresh()."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=8, pady=8)
        self.scroll.grid_columnconfigure((0, 1), weight=1, uniform="col")

    # -- public ------------------------------------------------------------
    def refresh(self):
        clear(self.scroll)
        try:
            data = build_dashboard(now=self.app.now(), db_path=self.app.db_path)
        except Exception as exc:  # keep the app alive; tell the student what happened
            muted_label(self.scroll, f"Could not load the dashboard: {exc}").grid(
                row=0, column=0, columnspan=2, padx=16, pady=16, sticky="w")
            return
        self._render(data)

    # -- layout --------------------------------------------------------------
    def _render(self, d):
        s = self.scroll
        header = ctk.CTkFrame(s, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 12))
        ctk.CTkLabel(header, text=d["greeting"], font=font(28, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(anchor="w")
        muted_label(header, d["date_text"], size=14).pack(anchor="w")

        row = 1
        if d["course_count"] == 0:
            card = Card(s, "Let's get you started")
            card.grid(row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=6)
            body_label(card.body, "Add your first course, then your timetable, "
                       "assignments, attendance and notes will fill this page in.").pack(anchor="w")
            ctk.CTkButton(card.body, text="Add a course", fg_color=theme.PRIMARY,
                          hover_color=theme.PRIMARY_HOVER, text_color="white",
                          command=lambda: self.app.navigate("courses")
                          ).pack(anchor="w", pady=(10, 0))
            row += 1

        self._stat_row(s, d).grid(row=row, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        row += 1

        left = ctk.CTkFrame(s, fg_color="transparent")
        right = ctk.CTkFrame(s, fg_color="transparent")
        left.grid(row=row, column=0, sticky="new", padx=6)
        right.grid(row=row, column=1, sticky="new", padx=6)
        self._classes_card(left, d).pack(fill="x", pady=6)
        self._next_class_card(left, d).pack(fill="x", pady=6)
        self._assignments_card(right, d).pack(fill="x", pady=6)
        self._attendance_card(right, d).pack(fill="x", pady=6)
        row += 1

        self._notes_card(s, d).grid(row=row, column=0, columnspan=2, sticky="ew",
                                    padx=12, pady=6)

    def _stat_row(self, parent, d):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")
        a, att = d["assignments"], d["attendance"]["overall"]
        pct = "-" if att["percentage"] is None else f"{att['percentage']}%"
        tiles = [
            StatTile(frame, "Classes today", len(d["todays_classes"]), "on your timetable"),
            StatTile(frame, "Pending assignments", a["pending"],
                     f"{a['due_today']} due today"),
            StatTile(frame, "Overdue", a["overdue"],
                     "needs attention" if a["overdue"] else "all caught up",
                     value_color=theme.DANGER if a["overdue"] else theme.TEXT),
            StatTile(frame, "Attendance", pct, d["attendance"]["standing"],
                     value_color=theme.DANGER if att["below_threshold"] else theme.TEXT),
        ]
        for i, tile in enumerate(tiles):
            tile.grid(row=0, column=i, sticky="nsew", padx=6)
        return frame

    def _classes_card(self, parent, d):
        card = Card(parent, "Today's classes", "Timetable", lambda: self.app.navigate("timetable"))
        if not d["todays_classes"]:
            muted_label(card.body, "No classes today.").pack(anchor="w")
        for i, c in enumerate(d["todays_classes"]):
            if i:
                divider(card.body).pack(fill="x", pady=6)
            line = ctk.CTkFrame(card.body, fg_color="transparent")
            line.pack(fill="x")
            body_label(line, f"{c['start_time']} - {c['end_time']}", weight="bold").pack(side="left")
            Badge(line, c["status"], theme.CLASS_STATUS_COLORS[c["status"]]).pack(side="right")
            body_label(card.body, f"{c['course_code']}  {c['course_name']}").pack(anchor="w")
            if c["venue"]:
                muted_label(card.body, c["venue"], size=12).pack(anchor="w")
        return card

    def _next_class_card(self, parent, d):
        card = Card(parent, "Next class")
        n = d["next_class"]
        if not n:
            muted_label(card.body, "Your timetable is empty.").pack(anchor="w")
            return card
        body_label(card.body, n["when_text"], size=18, weight="bold").pack(anchor="w")
        body_label(card.body, f"{n['course_code']}  {n['course_name']}").pack(anchor="w")
        muted_label(card.body, f"{n['start_time']} - {n['end_time']}"
                    + (f"  |  {n['venue']}" if n["venue"] else ""), size=12).pack(anchor="w")
        return card

    def _assignments_card(self, parent, d):
        a = d["assignments"]
        card = Card(parent, "Assignments", "View all", lambda: self.app.navigate("assignments"))
        if not a["items"]:
            muted_label(card.body, "Nothing pending. Nice work!").pack(anchor="w")
        for i, item in enumerate(a["items"]):
            if i:
                divider(card.body).pack(fill="x", pady=6)
            line = ctk.CTkFrame(card.body, fg_color="transparent")
            line.pack(fill="x")
            Badge(line, item["state"], theme.ASSIGNMENT_STATE_COLORS[item["state"]]
                  ).pack(side="right")
            body_label(line, item["title"], weight="bold", wraplength=230).pack(side="left")
            muted_label(card.body, f"{item['course_code']}  |  {item['due_text']}  |  "
                        f"{item['priority']} priority", size=12).pack(anchor="w")
        if a["pending"] > len(a["items"]):
            muted_label(card.body, f"+ {a['pending'] - len(a['items'])} more", size=12
                        ).pack(anchor="w", pady=(6, 0))
        return card

    def _attendance_card(self, parent, d):
        att = d["attendance"]
        card = Card(parent, "Attendance", "Details", lambda: self.app.navigate("attendance"))
        overall = att["overall"]
        if overall["percentage"] is None:
            muted_label(card.body, "No attendance recorded yet.").pack(anchor="w")
            return card
        body_label(card.body, f"{overall['percentage']}% overall  -  {att['standing']}",
                   weight="bold").pack(anchor="w")
        muted_label(card.body, f"Warning threshold: {overall['threshold']:g}%",
                    size=12).pack(anchor="w")
        if att["below"]:
            divider(card.body).pack(fill="x", pady=8)
            body_label(card.body, "Below the threshold:", size=13, weight="bold").pack(anchor="w")
            for s in att["below"]:
                pct = "-" if s["percentage"] is None else f"{s['percentage']}%"
                ctk.CTkLabel(card.body, text=f"{s['course_code']}  {pct}", font=font(13),
                             text_color=theme.DANGER, anchor="w").pack(anchor="w")
        return card

    def _notes_card(self, parent, d):
        card = Card(parent, "Recent notes", "All notes", lambda: self.app.navigate("notes"))
        if not d["recent_notes"]:
            muted_label(card.body, "No notes yet.").pack(anchor="w")
        for i, n in enumerate(d["recent_notes"]):
            if i:
                divider(card.body).pack(fill="x", pady=6)
            line = ctk.CTkFrame(card.body, fg_color="transparent")
            line.pack(fill="x")
            body_label(line, n["title"], weight="bold").pack(side="left")
            muted_label(line, n["updated_date"], size=12).pack(side="right")
            tags = ("  |  " + ", ".join(n["tags"])) if n["tags"] else ""
            muted_label(card.body, f"{n['course_code']}{tags}", size=12).pack(anchor="w")
        return card
