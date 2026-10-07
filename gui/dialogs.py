"""Shared dialogs (Partition B, Member B1) - used by EVERY screen.

    confirm(parent, "Delete course?", "This removes ...", "Delete", danger=True) -> bool
    show_error(parent, "Course code is required.")
    show_info(parent, "Backup saved to ...")

    FormDialog(parent, "Add course", fields=[Field("code", "Course code"), ...],
               on_submit=lambda v: courses.add_course(**v, db_path=app.db_path)).show()

FormDialog is the important one. The `on_submit` callback receives a dict of the
values; if a Partition A function raises ValueError / LookupError, the dialog
shows that message under the form and STAYS OPEN, so a student can fix the typo.
That is why Partition A puts student-safe wording in its exceptions.

The small pure helpers at the top (Field, normalize_choices, find_missing_required)
have no widgets, so they are unit-tested without a display.
"""
from dataclasses import dataclass, field as dc_field

import customtkinter as ctk

from student_os.ui import theme
from student_os.ui.theme import font

FIELD_KINDS = ("text", "multiline", "choice", "date")


# ---------------------------------------------------------------------------
# Pure helpers (no widgets)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Field:
    """Describes one input in a FormDialog.

    name     key in the dict handed to on_submit (match the Partition A argument name)
    kind     'text' | 'multiline' | 'choice' | 'date' (date = text box expecting YYYY-MM-DD)
    choices  for kind='choice': ['High','Low'] or [('CSC301 - Algorithms', 3), ...]
             (a pair is (label shown, value returned))
    initial  starting value (for choice: the VALUE, not the label)
    """
    name: str
    label: str
    kind: str = "text"
    required: bool = False
    initial: object = ""
    placeholder: str = ""
    choices: tuple = dc_field(default_factory=tuple)

    def __post_init__(self):
        if self.kind not in FIELD_KINDS:
            raise ValueError(f"Field kind must be one of {FIELD_KINDS}, not {self.kind!r}.")


def normalize_choices(choices):
    """['a','b'] or [('Label', value)] -> [('a','a'), ('b','b')] / [('Label', value)]."""
    pairs = []
    for item in choices:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            pairs.append((str(item[0]), item[1]))
        else:
            pairs.append((str(item), item))
    return pairs


def find_missing_required(fields, values):
    """Labels of required fields whose value is empty/None."""
    missing = []
    for f in fields:
        if not f.required:
            continue
        value = values.get(f.name)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(f.label)
    return missing


# ---------------------------------------------------------------------------
# Base window
# ---------------------------------------------------------------------------
class ModalDialog(ctk.CTkToplevel):
    """A centred pop-up that blocks the main window until it is closed."""

    def __init__(self, parent, title, width=420, height=200, closable=True):
        root = parent.winfo_toplevel()
        super().__init__(root)
        self.result = None
        self._closable = closable
        self.title(title)
        self.resizable(False, False)
        x = max(0, root.winfo_rootx() + (root.winfo_width() - width) // 2)
        y = max(0, root.winfo_rooty() + (root.winfo_height() - height) // 3)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.transient(root)
        self.protocol("WM_DELETE_WINDOW", self.cancel if closable else (lambda: None))
        if closable:
            self.bind("<Escape>", lambda _e: self.cancel())
        # grab_set() fails on Linux if the window is not on screen yet, so wait a moment.
        self.after(150, self._grab)

    def _grab(self):
        try:
            self.lift()
            self.grab_set()
            self.focus_force()
        except Exception:
            pass  # a missing grab only means the window is not strictly modal

    def close(self, result=None):
        self.result = result
        self.destroy()

    def cancel(self):
        self.close(None)

    def show(self):
        """Block until closed; return whatever was passed to close()."""
        self.wait_window(self)
        return self.result


# ---------------------------------------------------------------------------
# Message / confirm
# ---------------------------------------------------------------------------
class _ButtonDialog(ModalDialog):
    def __init__(self, parent, title, message, buttons, width=440):
        lines = sum(max(1, -(-len(part) // 54)) for part in str(message).split("\n"))
        super().__init__(parent, title, width=width, height=130 + 20 * lines)
        ctk.CTkLabel(self, text=message, font=font(14), text_color=theme.TEXT,
                     wraplength=width - 48, justify="left", anchor="w"
                     ).pack(fill="x", padx=24, pady=(24, 12))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(side="bottom", fill="x", padx=24, pady=(0, 20))
        for text, value, kind in reversed(buttons):
            ctk.CTkButton(row, text=text, width=96, command=lambda v=value: self.close(v),
                          **_button_style(kind)).pack(side="right", padx=(8, 0))


def _button_style(kind):
    if kind == "danger":
        return dict(fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER, text_color="white")
    if kind == "primary":
        return dict(fg_color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER, text_color="white")
    return dict(fg_color="transparent", border_width=1, border_color=theme.BORDER,
                text_color=theme.TEXT, hover_color=theme.BG)


def confirm(parent, title, message, confirm_text="Confirm", danger=False, cancel_text="Cancel"):
    """Yes/No question. Returns True only if the student clicked the confirm button."""
    buttons = [(cancel_text, False, "neutral"),
               (confirm_text, True, "danger" if danger else "primary")]
    return bool(_ButtonDialog(parent, title, message, buttons).show())


def show_error(parent, message, title="Something went wrong"):
    _ButtonDialog(parent, title, message, [("OK", None, "primary")]).show()


def show_info(parent, message, title="Student OS"):
    _ButtonDialog(parent, title, message, [("OK", None, "primary")]).show()


# ---------------------------------------------------------------------------
# Form dialog
# ---------------------------------------------------------------------------
class FormDialog(ModalDialog):
    """A generic add/edit form built from a list of Field objects.

    on_submit(values_dict) is called when the student clicks the submit button.
      - return anything   -> dialog closes; show() returns that value (True if None)
      - raise ValueError / LookupError -> message shown inline, dialog stays open
    cancelable=False hides Cancel and ignores the window's X (used for first-run setup).
    """

    def __init__(self, parent, title, fields, on_submit, submit_text="Save",
                 cancelable=True, width=460, intro=None):
        fields = list(fields)
        height = 150 + (34 if intro else 0) + sum(
            150 if f.kind == "multiline" else 72 for f in fields)
        super().__init__(parent, title, width=width, height=height, closable=cancelable)
        self.fields = fields
        self._on_submit = on_submit
        self._inputs = {}       # name -> widget
        self._choice_map = {}   # name -> {label: value}

        if intro:
            ctk.CTkLabel(self, text=intro, font=font(13), text_color=theme.TEXT_MUTED,
                         wraplength=width - 56, justify="left", anchor="w"
                         ).pack(fill="x", padx=28, pady=(20, 0))
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=28, pady=(16, 0))
        for f in self.fields:
            self._add_field(form, f)

        self._error = ctk.CTkLabel(self, text="", font=font(13), text_color=theme.DANGER,
                                   wraplength=width - 56, justify="left", anchor="w")
        self._error.pack(fill="x", padx=28, pady=(4, 0))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=(8, 20))
        ctk.CTkButton(row, text=submit_text, width=100, command=self.submit,
                      **_button_style("primary")).pack(side="right")
        if cancelable:
            ctk.CTkButton(row, text="Cancel", width=100, command=self.cancel,
                          **_button_style("neutral")).pack(side="right", padx=(0, 8))

    # -- building ---------------------------------------------------------
    def _add_field(self, form, f):
        text = f.label + (" *" if f.required else "")
        ctk.CTkLabel(form, text=text, font=font(13, "bold"), text_color=theme.TEXT,
                     anchor="w").pack(fill="x", pady=(8, 2))
        if f.kind == "multiline":
            box = ctk.CTkTextbox(form, height=90)
            if f.initial:
                box.insert("1.0", str(f.initial))
            box.pack(fill="x")
            self._inputs[f.name] = box
        elif f.kind == "choice":
            pairs = normalize_choices(f.choices) or [("(nothing to choose from)", None)]
            self._choice_map[f.name] = dict(pairs)
            labels = [label for label, _ in pairs]
            chosen = next((label for label, value in pairs if value == f.initial), labels[0])
            menu = ctk.CTkOptionMenu(form, values=labels, dynamic_resizing=False)
            menu.set(chosen)
            menu.pack(fill="x")
            self._inputs[f.name] = menu
        else:  # text / date
            placeholder = f.placeholder or ("YYYY-MM-DD" if f.kind == "date" else "")
            entry = ctk.CTkEntry(form, placeholder_text=placeholder)
            if f.initial not in ("", None):
                entry.insert(0, str(f.initial))
            entry.pack(fill="x")
            self._inputs[f.name] = entry

    # -- reading / submitting ----------------------------------------------
    def collect(self):
        """Current form contents as {field name: value}."""
        values = {}
        for f in self.fields:
            widget = self._inputs[f.name]
            if f.kind == "multiline":
                values[f.name] = widget.get("1.0", "end").strip()
            elif f.kind == "choice":
                values[f.name] = self._choice_map[f.name].get(widget.get())
            else:
                values[f.name] = widget.get().strip()
        return values

    def set_error(self, message):
        self._error.configure(text=message)

    def submit(self):
        values = self.collect()
        missing = find_missing_required(self.fields, values)
        if missing:
            self.set_error("Please fill in: " + ", ".join(missing) + ".")
            return
        try:
            outcome = self._on_submit(values)
        except (ValueError, LookupError) as exc:   # Partition A's student-safe messages
            self.set_error(str(exc))
            return
        except Exception as exc:                    # a bug - show it, don't crash the app
            self.set_error(f"Unexpected error: {exc}")
            return
        self.close(True if outcome is None else outcome)
