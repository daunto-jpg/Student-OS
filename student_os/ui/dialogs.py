"""Shared dialogs (Partition B, Member B1)."""
from dataclasses import dataclass, field as dc_field
import customtkinter as ctk
from student_os.ui import theme
from student_os.ui.theme import font
FIELD_KINDS=("text","multiline","choice","date")
@dataclass(frozen=True)
class Field:
    name:str; label:str; kind:str="text"; required:bool=False; initial:object=""; placeholder:str=""; choices:tuple=dc_field(default_factory=tuple)
    def __post_init__(self):
        if self.kind not in FIELD_KINDS: raise ValueError(f"Field kind must be one of {FIELD_KINDS}, not {self.kind!r}.")
def normalize_choices(choices):
    pairs=[]
    for item in choices:
        if isinstance(item,(tuple,list)) and len(item)==2: pairs.append((str(item[0]),item[1]))
        else: pairs.append((str(item),item))
    return pairs
def find_missing_required(fields,values):
    return [f.label for f in fields if f.required and (values.get(f.name) is None or (isinstance(values.get(f.name),str) and not values.get(f.name).strip()))]
class ModalDialog(ctk.CTkToplevel):
    def __init__(self,parent,title,width=420,height=200,closable=True):
        root=parent.winfo_toplevel(); super().__init__(root); self.result=None; self._closable=closable
        self.title(title); self.resizable(False,False)
        x=max(0,root.winfo_rootx()+(root.winfo_width()-width)//2); y=max(0,root.winfo_rooty()+(root.winfo_height()-height)//3)
        self.geometry(f"{width}x{height}+{x}+{y}"); self.transient(root)
        self.protocol("WM_DELETE_WINDOW",self.cancel if closable else (lambda:None))
        if closable: self.bind("<Escape>",lambda _e:self.cancel())
        self.after(150,self._grab)
    def _grab(self):
        try: self.lift(); self.grab_set(); self.focus_force()
        except Exception: pass
    def close(self,result=None): self.result=result; self.destroy()
    def cancel(self): self.close(None)
    def show(self): self.wait_window(self); return self.result
class _ButtonDialog(ModalDialog):
    def __init__(self,parent,title,message,buttons,width=440):
        lines=sum(max(1,-(-len(part)//54)) for part in str(message).split("\n"))
        super().__init__(parent,title,width=width,height=130+20*lines)
        ctk.CTkLabel(self,text=message,font=font(14),text_color=theme.TEXT,wraplength=width-48,justify="left",anchor="w").pack(fill="x",padx=24,pady=(24,12))
        row=ctk.CTkFrame(self,fg_color="transparent"); row.pack(side="bottom",fill="x",padx=24,pady=(0,20))
        for text,value,kind in reversed(buttons):
            ctk.CTkButton(row,text=text,width=96,command=lambda v=value:self.close(v),**_button_style(kind)).pack(side="right",padx=(8,0))
def _button_style(kind):
    if kind=="danger": return dict(fg_color=theme.DANGER,hover_color=theme.DANGER_HOVER,text_color="white")
    if kind=="primary": return dict(fg_color=theme.PRIMARY,hover_color=theme.PRIMARY_HOVER,text_color="white")
    return dict(fg_color="transparent",border_width=1,border_color=theme.BORDER,text_color=theme.TEXT,hover_color=theme.BG)
def confirm(parent,title,message,confirm_text="Confirm",danger=False,cancel_text="Cancel"):
    return bool(_ButtonDialog(parent,title,message,[(cancel_text,False,"neutral"),(confirm_text,True,"danger" if danger else "primary")]).show())
def show_error(parent,message,title="Something went wrong"): _ButtonDialog(parent,title,message,[("OK",None,"primary")]).show()
def show_info(parent,message,title="Student OS"): _ButtonDialog(parent,title,message,[("OK",None,"primary")]).show()
class FormDialog(ModalDialog):
    def __init__(self,parent,title,fields,on_submit,submit_text="Save",cancelable=True,width=460,intro=None):
        fields=list(fields); height=150+(34 if intro else 0)+sum(150 if f.kind=="multiline" else 72 for f in fields)
        super().__init__(parent,title,width=width,height=height,closable=cancelable); self.fields=fields; self._on_submit=on_submit; self._inputs={}; self._choice_map={}
        if intro: ctk.CTkLabel(self,text=intro,font=font(13),text_color=theme.TEXT_MUTED,wraplength=width-56,justify="left",anchor="w").pack(fill="x",padx=28,pady=(20,0))
        form=ctk.CTkFrame(self,fg_color="transparent"); form.pack(fill="both",expand=True,padx=28,pady=(16,0))
        for f in self.fields: self._add_field(form,f)
        self._error=ctk.CTkLabel(self,text="",font=font(13),text_color=theme.DANGER,wraplength=width-56,justify="left",anchor="w"); self._error.pack(fill="x",padx=28,pady=(4,0))
        row=ctk.CTkFrame(self,fg_color="transparent"); row.pack(fill="x",padx=28,pady=(8,20))
        ctk.CTkButton(row,text=submit_text,width=100,command=self.submit,**_button_style("primary")).pack(side="right")
        if cancelable: ctk.CTkButton(row,text="Cancel",width=100,command=self.cancel,**_button_style("neutral")).pack(side="right",padx=(0,8))
    def _add_field(self,form,f):
        ctk.CTkLabel(form,text=f.label+(" *" if f.required else ""),font=font(13,"bold"),text_color=theme.TEXT,anchor="w").pack(fill="x",pady=(8,2))
        if f.kind=="multiline":
            box=ctk.CTkTextbox(form,height=90)
            if f.initial: box.insert("1.0",str(f.initial))
            box.pack(fill="x"); self._inputs[f.name]=box
        elif f.kind=="choice":
            pairs=normalize_choices(f.choices) or [("(nothing to choose from)",None)]; self._choice_map[f.name]=dict(pairs); labels=[label for label,_ in pairs]
            chosen=next((label for label,value in pairs if value==f.initial),labels[0]); menu=ctk.CTkOptionMenu(form,values=labels,dynamic_resizing=False); menu.set(chosen); menu.pack(fill="x"); self._inputs[f.name]=menu
        else:
            entry=ctk.CTkEntry(form,placeholder_text=f.placeholder or ("YYYY-MM-DD" if f.kind=="date" else ""))
            if f.initial not in ("",None): entry.insert(0,str(f.initial))
            entry.pack(fill="x"); self._inputs[f.name]=entry
    def collect(self):
        values={}
        for f in self.fields:
            w=self._inputs[f.name]
            if f.kind=="multiline": values[f.name]=w.get("1.0","end").strip()
            elif f.kind=="choice": values[f.name]=self._choice_map[f.name].get(w.get())
            else: values[f.name]=w.get().strip()
        return values
    def set_error(self,message): self._error.configure(text=message)
    def submit(self):
        values=self.collect(); missing=find_missing_required(self.fields,values)
        if missing: self.set_error("Please fill in: "+", ".join(missing)+"."); return
        try: outcome=self._on_submit(values)
        except (ValueError,LookupError) as exc: self.set_error(str(exc)); return
        except Exception as exc: self.set_error(f"Unexpected error: {exc}"); return
        self.close(True if outcome is None else outcome)
