"""A stand-in for customtkinter so GUI code can be exercised with NO display.

It records the widget tree (parents, text, commands) so tests can look for
labels and click buttons. It proves our code runs and wires up correctly; it
does NOT prove how anything looks - that still needs a run on a real desktop.
"""
import sys
import types


class Widget:
    def __init__(self, master=None, *args, **kw):
        self.master = master
        self.kw = dict(kw)
        self.children = []
        self.scheduled = []
        self.destroyed = False
        self.text = kw.get("text")
        self._value = ""
        if "values" in kw and kw["values"]:
            self._value = kw["values"][0]
        if isinstance(master, Widget):
            master.children.append(self)

    # tree
    def winfo_children(self):
        return list(self.children)

    def destroy(self):
        self.destroyed = True
        if isinstance(self.master, Widget) and self in self.master.children:
            self.master.children.remove(self)
        for child in list(self.children):
            child.destroy()

    def winfo_toplevel(self):
        w = self
        while isinstance(w.master, Widget):
            w = w.master
        return w

    # geometry numbers
    def winfo_rootx(self): return 100
    def winfo_rooty(self): return 100
    def winfo_width(self): return 1180
    def winfo_height(self): return 740

    # config
    def configure(self, **kw):
        self.kw.update(kw)
        if "text" in kw:
            self.text = kw["text"]
    config = configure

    def cget(self, key):
        return self.kw.get(key)

    # scheduling (never actually fires)
    def after(self, ms, fn=None, *args):
        self.scheduled.append((ms, fn))
        return f"job{len(self.scheduled)}"

    def after_cancel(self, job):
        pass

    # input widgets
    def get(self, *args):
        return self._value

    def set(self, value):
        self._value = value

    def insert(self, index, text):
        self._value = str(text)

    def wait_window(self, *a):
        pass

    def __getattr__(self, name):   # grid, pack, bind, tkraise, geometry, ... -> no-ops
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: None


def walk(widget):
    yield widget
    for child in widget.children:
        yield from walk(child)


def texts(widget):
    return [w.text for w in walk(widget) if isinstance(w.text, str) and w.text.strip()]


def find_buttons(widget, text):
    return [w for w in walk(widget) if isinstance(w.text, str)
            and w.text.strip() == text and "command" in w.kw]


def install():
    """Return a fake `customtkinter` module (caller puts it in sys.modules)."""
    mod = types.ModuleType("customtkinter")
    for name in ("CTk", "CTkToplevel", "CTkFrame", "CTkScrollableFrame", "CTkLabel",
                 "CTkButton", "CTkEntry", "CTkTextbox", "CTkOptionMenu"):
        setattr(mod, name, type(name, (Widget,), {}))
    mod.CTkFont = lambda **kw: ("font", tuple(sorted(kw.items())))
    mod.set_appearance_mode = lambda *a: None
    mod.set_default_color_theme = lambda *a: None
    return mod
