import customtkinter as ctk
from student_os import attendance, courses
from student_os.ui import dialogs, theme
from student_os.ui.widgets import Card, Badge, body_label, clear, muted_label, page_header, primary_button

class AttendanceView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app=app
        top=ctk.CTkFrame(self,fg_color="transparent"); top.grid_columnconfigure(0,weight=1)
        page_header(top,"Attendance","Record sessions and monitor your percentage").grid(row=0,column=0,sticky="w")
        primary_button(top,"Record attendance",self.record).grid(row=0,column=1,sticky="e")
        top.pack(fill="x",padx=20,pady=(18,8))
        self.area=ctk.CTkScrollableFrame(self,fg_color="transparent"); self.area.pack(fill="both",expand=True,padx=12,pady=(0,8))
    def refresh(self):
        clear(self.area)
        try: summaries=attendance.get_all_summaries(db_path=self.app.db_path)
        except Exception as exc: muted_label(self.area,f"Could not load attendance: {exc}").pack(padx=12,pady=12); return
        if not summaries: muted_label(self.area,"Add courses before recording attendance.").pack(padx=12,pady=12); return
        for s in summaries: self._summary(s).pack(fill="x",padx=8,pady=5)
    def _summary(self,s):
        card=Card(self.area,f'{s["course_code"]} - {s["course_name"]}')
        pct="—" if s["percentage"] is None else f'{s["percentage"]:.1f}%'
        body_label(card.body,f'Attendance: {pct} | Present {s["present"]}  Late {s["late"]}  Excused {s["excused"]}  Absent {s["absent"]}').pack(anchor="w")
        if s["below_threshold"]: Badge(card.body,f'Below {s["threshold"]:g}% threshold',theme.DANGER).pack(anchor="w",pady=(7,0))
        return card
    def record(self):
        choices=[(f'{c["code"]} - {c["name"]}',c["id"]) for c in courses.list_courses(db_path=self.app.db_path)]
        if not choices: dialogs.show_info(self,"Add a course first."); self.app.navigate("courses"); return
        f=dialogs.Field
        fields=[f("course_id","Course",kind="choice",choices=choices,required=True),
                f("date","Date",kind="date",required=True,initial=self.app.now().date().isoformat()),
                f("status","Status",kind="choice",choices=attendance.STATUSES,required=True)]
        result=dialogs.FormDialog(self,"Record attendance",fields,
            lambda v: attendance.record_attendance(**v,db_path=self.app.db_path),
            submit_text="Save").show()
        if result is not None: self.app.notify("Attendance saved"); self.refresh()
