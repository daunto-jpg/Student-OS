"""Settings screen (Partition B, Member B2).

Profile, attendance warning threshold, Gemini status and database backup.
Saving goes through Partition A (profile.py / settings.py), whose ValueError
messages are shown under the relevant card.
"""
import customtkinter as ctk

from student_os.ui import dialogs, settings_data, theme
from student_os.ui.theme import font
from student_os.ui.widgets import (Badge, Card, body_label, clear, muted_label,
                                   page_header, primary_button)

PROFILE_FIELDS = (
    ("name", "Your name", "e.g. Ada Obi"),
    ("academic_session", "Academic session", "e.g. 2026/2027"),
    ("semester", "Semester", "e.g. First"),
)


class SettingsView(ctk.CTkFrame):
    """View contract: __init__(master, app) and refresh()."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        page_header(self, "Settings", "Your profile, attendance warning, AI status and backup"
                    ).pack(fill="x", padx=20, pady=(18, 8))
        self.page = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.page.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._build_profile_card()
        self._build_threshold_card()
        self._build_gemini_card()
        self._build_backup_card()

    # -- construction (once) ---------------------------------------------------
    def _card(self, title):
        card = Card(self.page, title)
        card.pack(fill="x", padx=8, pady=6)
        return card

    def _message(self, parent):
        label = ctk.CTkLabel(parent, text="", font=font(13), text_color=theme.DANGER,
                             anchor="w", justify="left", wraplength=560)
        label.pack(fill="x", pady=(6, 0))
        return label

    def _build_profile_card(self):
        card = self._card("Profile")
        self.profile_entries = {}
        for key, label, placeholder in PROFILE_FIELDS:
            body_label(card.body, label, size=13, weight="bold").pack(fill="x", pady=(8, 2))
            entry = ctk.CTkEntry(card.body, placeholder_text=placeholder, width=360)
            entry.pack(anchor="w")
            self.profile_entries[key] = entry
        self.profile_message = self._message(card.body)
        primary_button(card.body, "Save profile", self.save_profile).pack(
            anchor="w", pady=(10, 0))

    def _build_threshold_card(self):
        card = self._card("Attendance warning")
        muted_label(card.body, "Courses whose attendance falls below this percentage are "
                    "flagged on the Dashboard.", size=13).pack(anchor="w")
        row = ctk.CTkFrame(card.body, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        self.threshold_entry = ctk.CTkEntry(row, width=100, placeholder_text="75")
        self.threshold_entry.pack(side="left")
        body_label(row, "%").pack(side="left", padx=(6, 12))
        primary_button(row, "Save threshold", self.save_threshold, width=130).pack(side="left")
        self.threshold_message = self._message(card.body)

    def _build_gemini_card(self):
        card = self._card("AI Assistant (Gemini)")
        self.gemini_row = ctk.CTkFrame(card.body, fg_color="transparent")
        self.gemini_row.pack(fill="x")

    def _build_backup_card(self):
        card = self._card("Backup")
        self.db_label = muted_label(card.body, "", size=12)
        self.db_label.pack(anchor="w")
        primary_button(card.body, "Back up database now", self.backup, width=190).pack(
            anchor="w", pady=(10, 0))
        self.backup_message = self._message(card.body)

    # -- public ---------------------------------------------------------------
    def refresh(self):
        data = settings_data.load_settings(self.app.db_path)
        for key, entry in self.profile_entries.items():
            self._fill(entry, data["profile"].get(key, ""))
        self._fill(self.threshold_entry, f"{data['threshold']:g}")
        for message in (self.profile_message, self.threshold_message, self.backup_message):
            message.configure(text="")
        gem = data["gemini"]
        clear(self.gemini_row)
        Badge(self.gemini_row, gem["badge"],
              theme.BADGE_GREEN if gem["configured"] else theme.BADGE_AMBER
              ).pack(anchor="w")
        muted_label(self.gemini_row, gem["text"], size=13, wraplength=560).pack(
            anchor="w", pady=(8, 0))
        self.db_label.configure(text=f"Database file: {data['db_file']}")

    @staticmethod
    def _fill(entry, text):
        entry.delete(0, "end")
        if text:
            entry.insert(0, text)

    # -- actions --------------------------------------------------------------
    def save_profile(self):
        values = {key: entry.get().strip() for key, entry in self.profile_entries.items()}
        try:
            settings_data.save_profile(values, self.app.db_path)
        except (ValueError, LookupError) as exc:
            self.profile_message.configure(text=str(exc))
            return
        self.profile_message.configure(text="")
        self.app.refresh_identity()
        self.app.notify("Profile saved")

    def save_threshold(self):
        try:
            value = settings_data.save_threshold(self.threshold_entry.get(), self.app.db_path)
        except (ValueError, LookupError) as exc:
            self.threshold_message.configure(text=str(exc))
            return
        self.threshold_message.configure(text="")
        self._fill(self.threshold_entry, f"{value:g}")
        self.app.notify(f"Attendance warning set to {settings_data.threshold_text(value)}")

    def backup(self):
        try:
            path = settings_data.make_backup(self.app.db_path)
        except Exception as exc:
            self.backup_message.configure(text=f"Backup failed: {exc}")
            return
        self.backup_message.configure(text="")
        self.app.notify("Backup created")
        dialogs.show_info(self, f"Backup saved to:\n{path}")
