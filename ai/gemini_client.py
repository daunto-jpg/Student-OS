"""Gemini API client wrapper (Partition C, Member C1).

One small class between Student OS and the Google SDK:
  * checks the key before any network call
  * calls Gemini with the shared system instruction
  * turns every failure into an AIError (safe message + reason code)
  * imports the SDK only when a real request is made, so the app starts and
    runs offline even if the SDK is missing

`transport` can be replaced in tests with a fake function, so nothing in the
test suite needs a key, the SDK or an internet connection.
"""
from student_os.ai import config
from student_os.ai.errors import (
    AINotConfiguredError, AIResponseError, NO_KEY_MESSAGE, classify_exception,
)
from student_os.ai.prompts import SYSTEM_INSTRUCTION

TEMPERATURE = 0.3   # low: this is a study/data assistant, not a creative writer


def _sdk_transport(*, api_key, model, prompt, system_instruction, timeout):
    """The real call, using the google-genai SDK. Returns the reply text."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise AINotConfiguredError(
            "The Gemini library isn't installed. Run: pip install -r requirements.txt",
            reason="sdk_missing")
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(timeout * 1000)),   # SDK wants ms
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction, temperature=TEMPERATURE,
            # the app never gives Gemini tools; this also silences an SDK warning
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)),
    )
    return response.text or ""


class GeminiClient:
    def __init__(self, api_key=None, model=None, timeout=config.DEFAULT_TIMEOUT_SECONDS,
                 transport=None, environ=None):
        self._api_key = (api_key or "").strip() or config.get_api_key(environ)
        self.model = model or config.get_model_name(environ)
        self.timeout = timeout
        self._transport = transport or _sdk_transport

    def __repr__(self):                       # never print the key
        return f"GeminiClient(model={self.model!r}, configured={self.configured})"

    @property
    def configured(self):
        return self._api_key is not None

    def generate(self, prompt, system_instruction=SYSTEM_INSTRUCTION):
        """Send one prompt, return Gemini's reply text.

        Raises an AIError subclass on any failure (never a raw SDK/network error).
        """
        if not (prompt or "").strip():
            raise ValueError("Prompt is empty.")
        if not self.configured:
            raise AINotConfiguredError(NO_KEY_MESSAGE)
        try:
            text = self._transport(api_key=self._api_key, model=self.model, prompt=prompt,
                                   system_instruction=system_instruction,
                                   timeout=self.timeout)
        except Exception as exc:              # noqa: BLE001 - classify everything
            raise classify_exception(exc, self._api_key) from None
        text = (text or "").strip()
        if not text:
            raise AIResponseError(
                "Gemini didn't return an answer (it may have declined the request). "
                "Try rephrasing.")
        return text
