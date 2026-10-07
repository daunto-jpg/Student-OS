"""Colours and fonts shared by every screen (Partition B, Member B1).

Colours are (light_mode, dark_mode) tuples - CustomTkinter picks the right one
automatically when the appearance mode changes. Use these names instead of
typing hex codes in a view, so the whole app can be re-themed from this file.
"""
import customtkinter as ctk

APP_NAME = "Student OS"

# Surfaces
BG = ("#F3F5F9", "#12151C")
SURFACE = ("#FFFFFF", "#1C202A")
BORDER = ("#DDE2EC", "#2B3140")

# Sidebar (dark in both modes, like most desktop apps)
SIDEBAR = ("#1B2540", "#0D1017")
SIDEBAR_HOVER = ("#2A3862", "#1A2030")
SIDEBAR_ACTIVE = ("#3B6EF5", "#3B6EF5")
SIDEBAR_TEXT = "#E6EAF5"
SIDEBAR_MUTED = "#8E9AB8"

# Text
TEXT = ("#1B2333", "#E8EBF2")
TEXT_MUTED = ("#667085", "#98A2B8")

# Accents
PRIMARY = ("#2F63F0", "#5B8CFF")
PRIMARY_HOVER = ("#2450CC", "#7AA2FF")
DANGER = ("#D92D20", "#F97066")
DANGER_HOVER = ("#B42318", "#FDA29B")
WARNING = ("#B54708", "#FDB022")
SUCCESS = ("#067647", "#47CD89")

# Solid colours for badges (white text sits on top of these)
BADGE_RED = "#D92D20"
BADGE_AMBER = "#DC6803"
BADGE_GREEN = "#039855"
BADGE_BLUE = "#2F63F0"
BADGE_GREY = "#667085"

# Assignment state (from assignments.get_assignment_state) -> badge colour
ASSIGNMENT_STATE_COLORS = {
    "Overdue": BADGE_RED,
    "Due Today": BADGE_AMBER,
    "Due Soon": BADGE_AMBER,
    "Upcoming": BADGE_BLUE,
    "Completed": BADGE_GREEN,
}
# Class status (computed in dashboard_data) -> badge colour
CLASS_STATUS_COLORS = {
    "Ongoing": BADGE_GREEN,
    "Upcoming": BADGE_BLUE,
    "Finished": BADGE_GREY,
}

_FONTS = {}


def font(size=14, weight="normal"):
    """Cached CTkFont. (CTkFont needs a running window, so it is created lazily.)"""
    key = (size, weight)
    if key not in _FONTS:
        _FONTS[key] = ctk.CTkFont(size=size, weight=weight)
    return _FONTS[key]


def apply_global_theme(mode="system"):
    """Call once, before the first window is created."""
    ctk.set_appearance_mode(mode)      # "light" | "dark" | "system"
    ctk.set_default_color_theme("blue")
