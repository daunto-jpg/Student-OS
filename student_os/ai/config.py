"""Gemini settings and API-key handling (Partition C, Member C1).

The key is read from the GEMINI_API_KEY environment variable (loaded from a
local .env file when python-dotenv is installed). It is never written to the
database, never logged and never put in an error message - use redact() on
anything that might contain it.
"""
import os

GEMINI_KEY_ENV = "GEMINI_API_KEY"      # same name the Settings screen (B2) checks
GEMINI_MODEL_ENV = "GEMINI_MODEL"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 30


def load_env():
    """Load a local .env file if python-dotenv is installed (silently skip if not)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    return load_dotenv()


def _environ(environ):
    if environ is None:
        load_env()
        return os.environ
    return environ


def get_api_key(environ=None):
    """The API key, or None when it is missing/blank. Pass `environ` (a dict) in tests."""
    key = (_environ(environ).get(GEMINI_KEY_ENV) or "").strip()
    return key or None


def is_configured(environ=None):
    return get_api_key(environ) is not None


def get_model_name(environ=None):
    """Model to call. Override with GEMINI_MODEL in .env without touching code."""
    return (_environ(environ).get(GEMINI_MODEL_ENV) or "").strip() or DEFAULT_MODEL


def redact(text, key=None):
    """Replace the API key with [redacted] in any text before it is stored or shown."""
    text = str(text)
    if key:
        text = text.replace(key, "[redacted]")
    return text
