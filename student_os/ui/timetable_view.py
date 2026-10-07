import customtkinter as ctk
from student_os import courses,timetable
from student_os.ui import dialogs,theme,timetable_data
from student_os.ui.widgets import Card,body_label,clear,divider,muted_label,outline_button,page_header,primary_button
class TimetableView(ctk.CTkFrame):
    def __init__(self,master,app):
        super().__init__(master,fg_color="transparent"); self.app=app
        top=ctk.CTkFrame(self,fg_color="transparent"); top.grid_columnconfigure(0,weight=1); page_header(top,"Timetable","Your weekly class schedule").grid(row=0,column=0,sticky="w"); primary_button(top,"Add class",self.add_class).grid(row=0,column=1,sticky="e"); top.pack(fill="x",padx=20,pady=(18,4))
        self.next_label=body_label(self,"",size=14,weight="bold"); self.next_label.pack(fill="x",padx=22,pady=(0,6))
        self.week_area=ctk.CTkScrollableFrame(self,fg_color="transparent"); self.week_area.pack(fill="both",expand=True,padx=12,pady=(0,8)); self.week_area.grid_columnconfigure((0,1),weight=1,uniform="day")
    def refresh(self):
        clear(self.week_area)
        try: data=timetable_data.build_week(self.app.now(),self.app.db_path)
        except Exception as exc: self.next_label.configure(text=""); muted_label(self.week_area,f"Could not load the timetable: {exc}").grid(row=0,column=0,columnspan=2,padx=12,pady=12,sticky="w"); return
        self.next_label.configure(text=data["next_text"])
        for i,day in enumerate(data["days"]): self._day_card(day).grid(row=i//2,column=i%2,sticky="new",padx=6,pady=6)
    def _day_card(self,day):
        card=Card(self.week_area,day["day"]+("  (today)" if day["is_today"] else ""))
        if day["is_today"]: card.configure(border_color=theme.PRIMARY,border_width=2)
        if not day["slots"]: muted_label(card.body,"No classes").pack(anchor="w")
        for i,slot in enumerate(day["slots"]):
            if i: divider(card.body).pack(fill="x",pady=6)
            line=ctk.CTkFrame(card.body,fg_color="transparent"); line.pack(fill="x"); body_label(line,timetable_data.time_range(slot),weight="bold").pack(side="left")
            outline_button(line,"Delete",lambda s=slot:self.delete_slot(s),width=56,danger=True).pack(side="right"); outline_button(line,"Edit",lambda s=slot:self.edit_slot(s),width=48).pack(side="right",padx=(0,6))
            body_label(card.body,timetable_data.slot_title(slot),size=13).pack(anchor="w")
            if slot["venue"]: muted_label(card.body,slot["venue"],size=12).pack(anchor="w")
        return card
    def add_class(self):
        choices=timetable_data.course_choices(self.app.db_path)
        if not choices: dialogs.show_info(self,"Add a course first - every class belongs to a course."); self.app.navigate("courses"); return
        f=dialogs.Field
        result=dialogs.FormDialog(self,"Add class",fields=[f("course_id","Course",kind="choice",choices=choices,required=True),f("day_of_week","Day",kind="choice",choices=list(timetable.DAYS),initial=timetable.DAYS[self.app.now().weekday()]),f("start_time","Start time (24-hour)",required=True,placeholder="08:00"),f("end_time","End time (24-hour)",required=True,placeholder="10:00"),f("venue","Venue (optional)",placeholder="Leave blank to use the course venue")],submit_text="Add class",on_submit=lambda v:timetable.add_slot(**v,db_path=self.app.db_path)).show()
        if result is not None: self.app.notify("Class added"); self.refresh()
    def edit_slot(self,slot):
        course=courses.get_course(slot["course_id"],db_path=self.app.db_path); f=dialogs.Field
        result=dialogs.FormDialog(self,"Edit class",intro=f"{slot['course_code']} - {slot['course_name']}",fields=[f("day_of_week","Day",kind="choice",choices=list(timetable.DAYS),initial=slot["day_of_week"]),f("start_time","Start time (24-hour)",required=True,initial=slot["start_time"]),f("end_time","End time (24-hour)",required=True,initial=slot["end_time"]),f("venue","Venue (optional)",initial=timetable_data.editable_venue(slot,course),placeholder="Leave blank to use the course venue")],on_submit=lambda v:timetable.update_slot(slot["id"],**v,db_path=self.app.db_path)).show()
        if result is not None: self.app.notify("Class updated"); self.refresh()
    def delete_slot(self,slot):
        if not dialogs.confirm(self,"Delete class?",f"Delete {slot['course_code']} on {slot['day_of_week']} ({timetable_data.time_range(slot)})?","Delete",danger=True): return
        try: timetable.delete_slot(slot["id"],db_path=self.app.db_path)
        except LookupError as exc: self.app.show_error(str(exc))
        else: self.app.notify("Class deleted")
        self.refresh()
