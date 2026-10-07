import customtkinter as ctk
from student_os.ai.gemini_client import GeminiClient
from student_os.ai.errors import AINotConfiguredError
from student_os.ui.widgets import muted_label, page_header, primary_button

class AIAssistantView(ctk.CTkFrame):
    def __init__(self,master,app):
        super().__init__(master,fg_color="transparent"); self.app=app
        page_header(self,"AI Assistant","Ask Gemini for help with your studies").pack(fill="x",padx=20,pady=(18,8))
        self.output=ctk.CTkTextbox(self); self.output.pack(fill="both",expand=True,padx=20,pady=8); self.output.configure(state="disabled")
        bottom=ctk.CTkFrame(self,fg_color="transparent"); bottom.pack(fill="x",padx=20,pady=(0,8))
        self.prompt=ctk.CTkTextbox(bottom,height=90); self.prompt.pack(side="left",fill="x",expand=True)
        primary_button(bottom,"Ask AI",self.ask,width=100).pack(side="right",padx=(10,0))
        muted_label(self,"Requires GEMINI_API_KEY in the environment or .env file.",size=12).pack(anchor="w",padx=20,pady=(0,14))
    def refresh(self): pass
    def _write(self,text):
        self.output.configure(state="normal"); self.output.delete("1.0","end"); self.output.insert("end",text); self.output.configure(state="disabled")
    def ask(self):
        prompt=self.prompt.get("1.0","end").strip()
        if not prompt: self._write("Enter a question first."); return
        try:
            self._write(GeminiClient().generate(prompt)); self.app.notify("AI response received")
        except AINotConfiguredError as exc: self._write(str(exc))
        except Exception as exc: self._write(f"AI request failed: {exc}")
