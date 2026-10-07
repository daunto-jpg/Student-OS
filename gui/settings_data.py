"""Plain-Python helpers for the Settings screen (Partition B, Member B2).

No widgets and no SQL. Reading and saving go through Partition A
(profile.py and settings.py); this file only adapts them for the screen.

SECURITY: the Gemini API key is only ever checked for presence here. It is never
returned, displayed or logged.
"""
import os
from pathlib import Path

from student_os import db, profile, settings

GEMINI_KEY_ENV = "GEMINI_API_KEY"   # Partition C reads the same variable name
EMPTY_PROFILE = {"name": "", "academic_session": "", "semester": ""}


def _load_dotenv():
    try:
        from dotenv import load_dotenv
    except ImportError:          # python-dotenv not installed: plain env vars still work
        return
    load_dotenv()


def gemini_status(environ=None):
    """{'configured': bool, 'badge': str, 'text': str} - never includes the key itself."""
    if environ is None:
        _load_dotenv()
        environ = os.environ
    configured = bool((environ.get(GEMINI_KEY_ENV) or "").strip())
    if configured:
        text = ("A Gemini API key was found. AI features work when you are online; "
                "everything else works offline.")
    else:
        text = (f"No Gemini API key found. Add {GEMINI_KEY_ENV}=your-key to a file named "
                ".env next to main.py, then restart. The rest of Student OS works without it.")
    return {"configured": configured, "badge": "Key found" if configured else "Not set",
            "text": text}


def threshold_text(value):
    return f"{value:g}%"


def database_location(db_path=None):
    return str(Path(db_path) if db_path else db.get_db_path())


def load_settings(db_path=None, environ=None):
    return {
        "profile": profile.get_profile(db_path) or dict(EMPTY_PROFILE),
        "threshold": settings.get_attendance_threshold(db_path),
        "gemini": gemini_status(environ),
        "db_file": database_location(db_path),
    }


def save_profile(values, db_path=None):
    """values: dict with name / academic_session / semester. Raises ValueError (Partition A)."""
    return profile.save_profile(values.get("name"), values.get("academic_session", ""),
                                values.get("semester", ""), db_path=db_path)


def save_threshold(text, db_path=None):
    """Accepts '80' or '80%'. Raises ValueError (Partition A) for anything not 0-100."""
    return settings.set_attendance_threshold(str(text or "").strip().rstrip("%").strip(),
                                             db_path=db_path)


def make_backup(db_path=None):
    """Copy the database to a timestamped file; returns the new file's path."""
    return settings.backup_database(db_path=db_path)
