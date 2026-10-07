"""AI Assistant facade (Partition C, Member C2).

This is the ONE object the GUI (the AI tab and the note-level AI buttons)
needs. It joins the pieces:

    router -> context_builder -> prompts -> GeminiClient

and adds the offline fallback: no method here ever raises for a normal
failure. Each returns an AIResult, so the screen only has to show
`result.text` and can use `result.ok` / `result.reason` for styling.

Read-only by design: it imports only read functions through the context
builder and has no way to modify the database.
"""
from dataclasses import dataclass, field
from datetime import datetime

from student_os.ai import context_builder, prompts, router
from student_os.ai.errors import AIError
from student_os.ai.gemini_client import GeminiClient


@dataclass
class AIResult:
    ok: bool
    text: str
    feature: str
    reason: str = ""                 # '' when ok, else an AIError reason code (or 'invalid_input' / 'not_found')
    fallback: bool = False           # True when `text` is Python-built data, not Gemini's answer
    sections: list = field(default_factory=list)   # data sections that were used
    notice: str = ""                 # e.g. "Note was shortened to fit"


class Assistant:
    def __init__(self, client=None, db_path=None, clock=None):
        self.client = client or GeminiClient()
        self.db_path = db_path
        self._clock = clock or datetime.now

    # ------------------------------------------------------------- status
    @property
    def available(self):
        """True when a key is configured. (It does not test the connection.)"""
        return self.client.configured

    # ------------------------------------------------------------ plumbing
    def _fail(self, feature, exc, fallback_text="", sections=None):
        text = exc.user_message
        if fallback_text:
            text += ("\n\nGemini isn't available, but here is your saved data for "
                     "this question:\n\n" + fallback_text)
        return AIResult(False, text, feature, exc.reason, bool(fallback_text),
                        sections or [])

    def _run_note_feature(self, feature, note_id, **prompt_args):
        try:
            note = context_builder.build_note_context(note_id, self.db_path)
            prompt = prompts.build_prompt(feature, note=note, **prompt_args)
        except LookupError as exc:
            return AIResult(False, str(exc), feature, "not_found")
        except ValueError as exc:
            return AIResult(False, str(exc), feature, "invalid_input")
        notice = ("This note is very long, so only the first "
                  f"{context_builder.MAX_NOTE_CHARS:,} characters were used."
                  if note["truncated"] else "")
        try:
            return AIResult(True, self.client.generate(prompt), feature, notice=notice)
        except AIError as exc:
            result = self._fail(feature, exc)
            result.notice = notice
            return result

    # --------------------------------------------------------- the 5 features
    def ask(self, question, mode=router.AUTO):
        """General Q&A or academic overview, chosen by the router (or by `mode`)."""
        try:
            route = router.route_question(question, mode)
        except ValueError as exc:
            return AIResult(False, str(exc), prompts.GENERAL_QA, "invalid_input")

        if route.kind == "general":
            try:
                prompt = prompts.build_prompt(prompts.GENERAL_QA, question=question)
                return AIResult(True, self.client.generate(prompt), prompts.GENERAL_QA)
            except ValueError as exc:
                return AIResult(False, str(exc), prompts.GENERAL_QA, "invalid_input")
            except AIError as exc:
                return self._fail(prompts.GENERAL_QA, exc)

        feature = prompts.ACADEMIC_OVERVIEW
        context = context_builder.build_overview_context(
            route.topics, now=self._clock(), db_path=self.db_path)
        try:
            prompt = prompts.build_prompt(feature, question=question,
                                          context_text=context["text"])
        except ValueError as exc:
            return AIResult(False, str(exc), feature, "invalid_input")
        try:
            return AIResult(True, self.client.generate(prompt), feature,
                            sections=context["sections"])
        except AIError as exc:
            # Offline fallback: the facts are already calculated, so show them.
            return self._fail(feature, exc, context["text"], context["sections"])

    def explain_note(self, note_id, focus=None):
        return self._run_note_feature(prompts.EXPLAIN_NOTE, note_id, focus=focus)

    def summarize_note(self, note_id):
        return self._run_note_feature(prompts.SUMMARIZE_NOTE, note_id)

    def revision_questions(self, note_id, count=prompts.DEFAULT_QUESTIONS):
        return self._run_note_feature(prompts.REVISION_QUESTIONS, note_id, count=count)
