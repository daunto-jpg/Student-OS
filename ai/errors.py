"""Errors for the AI layer (Partition C, Member C1).

Every failure is turned into an AIError with a `user_message` that is safe to
show the student (no key, no stack trace) and a `reason` code the GUI can
branch on. `detail` is a redacted technical note for debugging only.

reason codes: no_key, sdk_missing, offline, service_down, bad_key,
              rate_limited, api_error, bad_response
"""
import socket

from student_os.ai.config import GEMINI_KEY_ENV, redact


class AIError(Exception):
    reason = "api_error"

    def __init__(self, user_message, detail="", reason=None):
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail
        if reason:
            self.reason = reason


class AINotConfiguredError(AIError):
    reason = "no_key"


class AIUnavailableError(AIError):
    reason = "offline"


class AIRequestError(AIError):
    reason = "api_error"


class AIResponseError(AIError):
    reason = "bad_response"


OFFLINE_MESSAGE = ("Can't reach Gemini. Check your internet connection and try again. "
                   "Everything except the AI Assistant still works offline.")
NO_KEY_MESSAGE = (f"No Gemini API key found. Add {GEMINI_KEY_ENV}=your-key to the .env file "
                  "next to main.py, then restart Student OS.")

# Exception class names that mean "the network is down / too slow". Matching on
# names (through the whole class hierarchy) means we need neither the SDK nor
# httpx imported to recognise them.
_NETWORK_NAMES = {"ConnectionError", "TimeoutError", "TransportError",
                  "TimeoutException", "gaierror"}


def classify_exception(exc, key=None):
    """Turn any exception from the Gemini SDK / network into an AIError."""
    if isinstance(exc, AIError):
        return exc
    names = {cls.__name__ for cls in type(exc).__mro__}
    detail = redact(f"{type(exc).__name__}: {exc}", key)
    code = getattr(exc, "code", None)
    code = code if isinstance(code, int) else None
    text = str(exc).lower()

    if isinstance(exc, (ConnectionError, TimeoutError, socket.gaierror)) or \
            names & _NETWORK_NAMES:
        return AIUnavailableError(OFFLINE_MESSAGE, detail)
    if code in (401, 403) or "api key" in text:
        return AIRequestError(
            f"Gemini refused the request. Check that {GEMINI_KEY_ENV} in your .env file "
            "is correct and allowed to use Gemini.",
            detail, reason="bad_key")
    if code == 429:
        return AIRequestError(
            "Gemini's usage limit was reached. Wait a minute and try again.",
            detail, reason="rate_limited")
    if (code is not None and code >= 500) or "ServerError" in names:
        return AIUnavailableError(
            "Gemini is having problems right now. Try again shortly.",
            detail, reason="service_down")
    if code == 404:
        return AIRequestError(
            "Gemini doesn't recognise the model name. Check GEMINI_MODEL in your .env file.",
            detail)
    return AIRequestError("Something went wrong while talking to Gemini. Try again.", detail)
