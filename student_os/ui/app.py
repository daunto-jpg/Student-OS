"""Main window: sidebar, screen switching, status bar (Partition B, Member B1)."""
import importlib
import traceback
from collections import namedtuple
from datetime import datetime

import customtkinter as ctk

from student_os import db, profile
from student_os.ui import dialogs, theme
from student_os.ui.theme import font

NavItem = namedtuple("NavItem", "key label module class_name")
NAV_ITEMS = [
    NavItem("dashboard", "Dashboard", "dashboard", "DashboardView"),
    NavItem("courses", "Courses", "courses_view", "CoursesView"),
    NavItem("timetable", "Timetable", "timetable_view", "TimetableView"),
    NavItem("assignments", "Assignments", "assignments_view", "AssignmentsView"),
    NavItem("attendance", "Attendance", "attendance_view", "AttendanceView"),
    NavItem("notes", "Notes", "notes_view", "NotesView"),
    NavItem("ai", "AI Assistant", "ai_view", "AIAssistantView"),
    NavItem("settings", "Settings", "settings_view", "SettingsView"),
]
NAV_BY_KEY = {item.key: item for item in NAV_ITEMS}

def load_view_class(item):
    module_name = f"student_os.ui.{item.module}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise
    return getattr(module, item.class_name, None)

class PlaceholderView(ctk.CTkFrame):
    def __init__(self, master, app, title):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=title, font=font(26, "bold"), text_color=theme.TEXT).pack(pady=(120, 6))
        ctk.CTkLabel(self, text="This screen is not built yet.", font=font(14), text_color=theme.TEXT_MUTED).pack()
    def refresh(self):
        pass

class ErrorView(ctk.CTkFrame):
    def __init__(self, master, app, title, detail):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=f"{title} could not be opened", font=font(22, "bold"), text_color=theme.DANGER).pack(pady=(100, 8))
        ctk.CTkLabel(self, text=detail, font=font(13), text_color=theme.TEXT_MUTED, wraplength=640, justify="left").pack(padx=40)
    def refresh(self):
        pass

class StudentOSApp(ctk.CTk):
    def __init__(self, db_path=None, clock=None, ask_profile=True):
        theme.apply_global_theme()
        super().__init__()
        self.db_path = db_path
        self._clock = clock or datetime.now
        db.init_db(self.db_path)
        self.title(theme.APP_NAME)
        self.geometry("1180x740")
        self.minsize(980, 620)
        self.configure(fg_color=theme.BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._views = {}
        self._nav_buttons = {}
        self._notify_job = None
        self.current = None
        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=(8, 0))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.status = ctk.CTkLabel(self, text="", font=font(12), text_color=theme.TEXT_MUTED, anchor="w")
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 6))
        for i, item in enumerate(NAV_ITEMS[:9], start=1):
            self.bind(f"<Control-Key-{i}>", lambda _e, k=item.key: self.navigate(k))
        self.refresh_identity()
        self.navigate("dashboard")
        if ask_profile:
            self.after(300, self.ensure_profile)
    def now(self):
        return self._clock()
    def navigate(self, key):
        if key not in NAV_BY_KEY:
            raise KeyError(f"Unknown screen: {key!r}")
        view = self._views.get(key) or self._build_view(NAV_BY_KEY[key])
        view.tkraise()
        self.current = key
        for k, button in self._nav_buttons.items():
            button.configure(fg_color=theme.SIDEBAR_ACTIVE if k == key else "transparent")
        try:
            view.refresh()
        except Exception as exc:
            self.show_error(f"Could not refresh {NAV_BY_KEY[key].label}: {exc}")
    def refresh_current(self):
        if self.current:
            self.navigate(self.current)
    def notify(self, message, seconds=4):
        if self._notify_job is not None:
            self.after_cancel(self._notify_job)
        self.status.configure(text=message)
        self._notify_job = self.after(int(seconds * 1000), lambda: self.status.configure(text=""))
    def show_error(self, message):
        dialogs.show_error(self, message)
    def refresh_identity(self):
        try:
            prof = profile.get_profile(self.db_path)
        except Exception:
            prof = None
        if prof:
            sub = " | ".join(p for p in (prof["academic_session"], prof["semester"]) if p)
            self.identity_name.configure(text=prof["name"])
            self.identity_sub.configure(text=sub or " ")
        else:
            self.identity_name.configure(text="Welcome")
            self.identity_sub.configure(text="Set up your profile")
    def ensure_profile(self):
        if profile.get_profile(self.db_path) is not None:
            return
        def save(values):
            profile.save_profile(values["name"], values["academic_session"], values["semester"], db_path=self.db_path)
        dialogs.FormDialog(self, "Welcome to Student OS",
            fields=[dialogs.Field("name", "Your name", required=True),
                    dialogs.Field("academic_session", "Academic session", placeholder="e.g. 2026/2027"),
                    dialogs.Field("semester", "Semester", placeholder="e.g. First")],
            on_submit=save, submit_text="Get started", cancelable=False,
            intro="Let's set up your profile. You can change this later in Settings.").show()
        self.refresh_identity()
        self.refresh_current()
    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=theme.SIDEBAR)
        bar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        bar.grid_propagate(False)
        bar.grid_rowconfigure(len(NAV_ITEMS) + 2, weight=1)
        ctk.CTkLabel(bar, text=theme.APP_NAME, font=font(22, "bold"), text_color=theme.SIDEBAR_TEXT, anchor="w").grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 0))
        ctk.CTkLabel(bar, text="Your academic life, in one place", font=font(11), text_color=theme.SIDEBAR_MUTED, anchor="w").grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        for i, item in enumerate(NAV_ITEMS):
            button = ctk.CTkButton(bar, text=item.label, anchor="w", height=40, corner_radius=8, font=font(14), fg_color="transparent", text_color=theme.SIDEBAR_TEXT, hover_color=theme.SIDEBAR_HOVER, command=lambda k=item.key: self.navigate(k))
            button.grid(row=i + 2, column=0, sticky="ew", padx=12, pady=2)
            self._nav_buttons[item.key] = button
        footer = ctk.CTkFrame(bar, fg_color="transparent")
        footer.grid(row=len(NAV_ITEMS) + 3, column=0, sticky="sew", padx=20, pady=20)
        self.identity_name = ctk.CTkLabel(footer, text="", font=font(14, "bold"), text_color=theme.SIDEBAR_TEXT, anchor="w")
        self.identity_name.pack(anchor="w")
        self.identity_sub = ctk.CTkLabel(footer, text="", font=font(12), text_color=theme.SIDEBAR_MUTED, anchor="w")
        self.identity_sub.pack(anchor="w")
    def _build_view(self, item):
        try:
            cls = load_view_class(item)
            if cls is None:
                view = PlaceholderView(self.content, self, item.label)
            else:
                view = cls(self.content, self)
        except Exception:
            detail = traceback.format_exc(limit=3)
            view = ErrorView(self.content, self, item.label, detail)
        view.grid(row=0, column=0, sticky="nsew")
        self._views[item.key] = view
        return view
