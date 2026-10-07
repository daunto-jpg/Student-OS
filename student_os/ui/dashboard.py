import customtkinter as ctk
from student_os.ui.dashboard_data import build_dashboard
from student_os.ui.widgets import Card,body_label,clear,muted_label,primary_button
class DashboardView(ctk.CTkFrame):
    def __init__(self,master,app):
        super().__init__(master,fg_color="transparent"); self.app=app; self.scroll=ctk.CTkScrollableFrame(self,fg_color="transparent"); self.scroll.pack(fill="both",expand=True,padx=8,pady=8)
    def refresh(self):
        clear(self.scroll)
        try: data=build_dashboard(now=self.app.now(),db_path=self.app.db_path)
        except Exception as exc: muted_label(self.scroll,f"Could not load the dashboard: {exc}").pack(padx=16,pady=16); return
        body_label(self.scroll,data["greeting"],size=28,weight="bold").pack(anchor="w",padx=16,pady=(12,0)); muted_label(self.scroll,data["date_text"]).pack(anchor="w",padx=16)
        if data["course_count"]==0:
            card=Card(self.scroll,"Let's get you started"); card.pack(fill="x",padx=12,pady=12); body_label(card.body,"Add your first course, then your timetable, assignments, attendance and notes will fill this page in.").pack(anchor="w"); primary_button(card.body,"Add a course",lambda:self.app.navigate("courses")).pack(anchor="w",pady=(10,0))
